"""Policy Engine - Core policy evaluation using OPA or local rules."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class PolicyAction(Enum):
    """Policy enforcement actions."""
    
    ALLOW = "allow"
    BLOCK = "block"
    CONFIRM = "confirm"  # Graylist - requires user confirmation
    LOG = "log"  # Allow but log for audit


@dataclass
class PolicyRule:
    """A single policy rule."""
    
    name: str
    description: str
    pattern: str  # Regex pattern
    action: PolicyAction
    severity: str = "medium"  # low, medium, high, critical
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Compile regex pattern."""
        self._compiled = re.compile(self.pattern, re.IGNORECASE)
    
    def matches(self, command: str) -> bool:
        """Check if command matches this rule."""
        return bool(self._compiled.search(command))


@dataclass
class PolicyResult:
    """Result of policy evaluation."""
    
    allowed: bool
    action: PolicyAction
    rule: PolicyRule | None = None
    message: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    
    @property
    def requires_confirmation(self) -> bool:
        """Check if this result requires user confirmation."""
        return self.action == PolicyAction.CONFIRM


class PolicyEngine:
    """Policy engine for evaluating commands against security policies."""
    
    def __init__(
        self,
        policy_dir: str | Path | None = None,
        opa_url: str | None = None,
        use_opa: bool = False,
    ) -> None:
        """Initialize policy engine.
        
        Args:
            policy_dir: Directory containing policy files
            opa_url: URL of OPA server (if using OPA)
            use_opa: Whether to use OPA for policy evaluation
        """
        self.policy_dir = Path(policy_dir) if policy_dir else Path(__file__).parent / "../../../policies"
        self.opa_url = opa_url or os.getenv("OPA_URL", "http://localhost:8181")
        self.use_opa = use_opa
        
        self._rules: list[PolicyRule] = []
        self._opa_available = False
        
        self._load_builtin_rules()
        self._load_policy_files()
        
        if use_opa:
            self._check_opa_availability()
    
    def _load_builtin_rules(self) -> None:
        """Load built-in security rules."""
        builtin_rules = [
            # Destructive operations
            PolicyRule(
                name="rm_rf_root",
                description="Block rm -rf / or similar destructive patterns",
                pattern=r"rm\s+-[a-zA-Z]*f[a-zA-Z]*\s+.*(/\s*|/\.\s*$|/\*)",
                action=PolicyAction.BLOCK,
                severity="critical",
            ),
            PolicyRule(
                name="mkfs_block",
                description="Block filesystem formatting",
                pattern=r"\bmkfs\.",
                action=PolicyAction.BLOCK,
                severity="critical",
            ),
            PolicyRule(
                name="dd_to_disk",
                description="Block dd to block devices",
                pattern=r"\bdd\s+.*of=/dev/[sh]d",
                action=PolicyAction.BLOCK,
                severity="critical",
            ),
            # Credential access
            PolicyRule(
                name="shadow_access",
                description="Block access to shadow password files",
                pattern=r"\bcat\s+/etc/(shadow|gshadow)",
                action=PolicyAction.BLOCK,
                severity="high",
            ),
            PolicyRule(
                name="ssh_key_access",
                description="Block access to SSH private keys",
                pattern=r"\bcat\s+.*/\.ssh/id_",
                action=PolicyAction.BLOCK,
                severity="high",
            ),
            # Privilege escalation
            PolicyRule(
                name="sudo_su",
                description="Block sudo su attempts",
                pattern=r"\bsudo\s+su\b",
                action=PolicyAction.CONFIRM,
                severity="high",
            ),
            # Network attacks
            PolicyRule(
                name="curl_pipe_bash",
                description="Block curl | bash patterns",
                pattern=r"curl\s+.*\|\s*(ba)?sh",
                action=PolicyAction.CONFIRM,
                severity="high",
            ),
            # System modification (graylist)
            PolicyRule(
                name="package_install",
                description="Confirm package installations",
                pattern=r"\b(apt|yum|dnf|pacman|pip|npm)\s+install",
                action=PolicyAction.CONFIRM,
                severity="medium",
            ),
            PolicyRule(
                name="service_restart",
                description="Confirm service restarts",
                pattern=r"\bsystemctl\s+(restart|stop)",
                action=PolicyAction.CONFIRM,
                severity="medium",
            ),
            PolicyRule(
                name="firewall_modify",
                description="Confirm firewall modifications",
                pattern=r"\b(iptables|ufw|firewalld)\s+.*(-A|--add|-D|--delete)",
                action=PolicyAction.CONFIRM,
                severity="high",
            ),
            # Kubernetes safety
            PolicyRule(
                name="kubectl_delete",
                description="Block kubectl delete without confirmation",
                pattern=r"\bkubectl\s+delete\s+.*--force|--grace-period=0",
                action=PolicyAction.BLOCK,
                severity="high",
            ),
            PolicyRule(
                name="kubectl_secret_access",
                description="Block kubectl get secret",
                pattern=r"\bkubectl\s+get\s+secret",
                action=PolicyAction.BLOCK,
                severity="high",
            ),
        ]
        self._rules.extend(builtin_rules)
    
    def _load_policy_files(self) -> None:
        """Load policy rules from JSON files."""
        if not self.policy_dir.exists():
            return
        
        for policy_file in self.policy_dir.glob("*.json"):
            try:
                with open(policy_file) as f:
                    data = json.load(f)
                
                for rule_data in data.get("rules", []):
                    rule = PolicyRule(
                        name=rule_data["name"],
                        description=rule_data["description"],
                        pattern=rule_data["pattern"],
                        action=PolicyAction(rule_data["action"]),
                        severity=rule_data.get("severity", "medium"),
                        metadata=rule_data.get("metadata", {}),
                    )
                    self._rules.append(rule)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Warning: Failed to load policy file {policy_file}: {e}")
    
    def _check_opa_availability(self) -> None:
        """Check if OPA server is available."""
        try:
            import httpx
            response = httpx.get(f"{self.opa_url}/health", timeout=2.0)
            self._opa_available = response.status_code == 200
        except Exception:
            self._opa_available = False
    
    def evaluate(self, command: str, context: dict[str, Any] | None = None) -> PolicyResult:
        """Evaluate a command against all policies.
        
        Args:
            command: The command to evaluate
            context: Additional context (user, cwd, etc.)
        
        Returns:
            PolicyResult with evaluation outcome
        """
        ctx = context or {}
        
        # Try OPA first if available
        if self.use_opa and self._opa_available:
            return self._evaluate_opa(command, ctx)
        
        # Fall back to local rule evaluation
        return self._evaluate_local(command, ctx)
    
    def _evaluate_local(self, command: str, context: dict[str, Any]) -> PolicyResult:
        """Evaluate using local rules."""
        # Check rules in order of severity (critical first)
        sorted_rules = sorted(
            self._rules,
            key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r.severity, 4)
        )
        
        for rule in sorted_rules:
            if rule.matches(command):
                return PolicyResult(
                    allowed=rule.action in (PolicyAction.ALLOW, PolicyAction.LOG, PolicyAction.CONFIRM),
                    action=rule.action,
                    rule=rule,
                    message=f"Policy '{rule.name}': {rule.description}",
                    context={"command": command, **context},
                )
        
        # No rules matched - allow by default
        return PolicyResult(
            allowed=True,
            action=PolicyAction.ALLOW,
            message="No policy restrictions apply",
            context={"command": command, **context},
        )
    
    def _evaluate_opa(self, command: str, context: dict[str, Any]) -> PolicyResult:
        """Evaluate using OPA server."""
        try:
            import httpx
            
            input_data = {
                "input": {
                    "command": command,
                    **context,
                }
            }
            
            response = httpx.post(
                f"{self.opa_url}/v1/data/sysadmin_ai/allow",
                json=input_data,
                timeout=5.0,
            )
            
            if response.status_code == 200:
                result = response.json()
                allowed = result.get("result", False)
                
                return PolicyResult(
                    allowed=allowed,
                    action=PolicyAction.ALLOW if allowed else PolicyAction.BLOCK,
                    message="OPA policy evaluation" if allowed else "OPA policy denied",
                    context={"command": command, "opa_result": result, **context},
                )
            else:
                # Fall back to local evaluation on OPA error
                return self._evaluate_local(command, context)
        except Exception as e:
            # Fall back to local evaluation on OPA error
            return PolicyResult(
                allowed=False,
                action=PolicyAction.BLOCK,
                message=f"OPA evaluation failed: {e}",
                context={"command": command, "error": str(e), **context},
            )
    
    def add_rule(self, rule: PolicyRule) -> None:
        """Add a custom rule to the engine."""
        self._rules.append(rule)
    
    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name."""
        for i, rule in enumerate(self._rules):
            if rule.name == name:
                self._rules.pop(i)
                return True
        return False
    
    def list_rules(self) -> list[PolicyRule]:
        """List all loaded rules."""
        return self._rules.copy()
    
    def dry_run(self, command: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Simulate policy evaluation without enforcement.
        
        Returns detailed information about what would happen.
        """
        result = self.evaluate(command, context)
        
        return {
            "command": command,
            "would_execute": result.allowed and not result.requires_confirmation,
            "requires_confirmation": result.requires_confirmation,
            "action": result.action.value,
            "rule_matched": result.rule.name if result.rule else None,
            "message": result.message,
            "all_matching_rules": [
                {"name": r.name, "action": r.action.value, "severity": r.severity}
                for r in self._rules
                if r.matches(command)
            ],
        }
