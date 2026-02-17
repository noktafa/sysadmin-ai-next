"""Open Policy Agent integration for declarative security policies."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class PolicyResult:
    """Result of policy evaluation."""

    allowed: bool
    reason: str | None = None
    violations: list[str] | None = None
    metadata: dict[str, Any] | None = None


class PolicyEngine:
    """Policy engine using Open Policy Agent (OPA).

    Falls back to local Rego evaluation if OPA server is unavailable.
    """

    def __init__(
        self,
        enabled: bool = True,
        opa_url: str = "http://localhost:8181",
        policy_dir: str | Path | None = None,
    ):
        self.enabled = enabled
        self.opa_url = opa_url.rstrip("/")
        self.policy_dir = Path(policy_dir) if policy_dir else Path(__file__).parent / "../../../policies"
        self.policy_dir = self.policy_dir.resolve()
        
        # Cache for loaded policies
        self._policies: dict[str, str] = {}
        self._opa_available: bool | None = None

        if enabled:
            self._load_policies()

    def _load_policies(self) -> None:
        """Load Rego policy files from policy directory."""
        if not self.policy_dir.exists():
            logger.warning(f"Policy directory not found: {self.policy_dir}")
            return

        for policy_file in self.policy_dir.glob("*.rego"):
            try:
                self._policies[policy_file.stem] = policy_file.read_text()
                logger.debug(f"Loaded policy: {policy_file.name}")
            except Exception as e:
                logger.error(f"Failed to load policy {policy_file}: {e}")

    async def _is_opa_available(self) -> bool:
        """Check if OPA server is available."""
        if self._opa_available is not None:
            return self._opa_available

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.opa_url}/health")
                self._opa_available = response.status_code == 200
        except Exception:
            self._opa_available = False

        return self._opa_available

    async def evaluate(
        self,
        command: str,
        context: dict[str, Any],
    ) -> PolicyResult:
        """Evaluate a command against security policies.

        Args:
            command: The command to evaluate
            context: Additional context (user, environment, etc.)

        Returns:
            PolicyResult with allow/deny decision
        """
        if not self.enabled:
            return PolicyResult(allowed=True)

        # Try OPA server first
        if await self._is_opa_available():
            return await self._evaluate_with_opa(command, context)

        # Fall back to local evaluation
        return await self._evaluate_locally(command, context)

    async def _evaluate_with_opa(
        self,
        command: str,
        context: dict[str, Any],
    ) -> PolicyResult:
        """Evaluate using OPA server."""
        input_data = {
            "command": command,
            "user": context.get("user", "anonymous"),
            "environment": context.get("environment", {}),
            "timestamp": context.get("timestamp"),
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.opa_url}/v1/data/sysadmin/allow",
                    json={"input": input_data},
                )
                response.raise_for_status()
                data = response.json()

                allowed = data.get("result", False)
                return PolicyResult(
                    allowed=allowed,
                    reason="OPA evaluation" if allowed else "Policy denied",
                    metadata={"source": "opa"},
                )
        except Exception as e:
            logger.warning(f"OPA evaluation failed, falling back: {e}")
            return await self._evaluate_locally(command, context)

    async def _evaluate_locally(
        self,
        command: str,
        context: dict[str, Any],
    ) -> PolicyResult:
        """Evaluate policies locally without OPA server."""
        violations = []

        # Built-in security policies
        if self._is_dangerous_command(command):
            violations.append("Command matches dangerous pattern")

        if self._has_destructive_flags(command):
            violations.append("Command has destructive flags")

        if self._accesses_sensitive_paths(command):
            violations.append("Command accesses sensitive paths")

        # Check user permissions from context
        user_perms = context.get("permissions", [])
        if "admin" not in user_perms and self._requires_admin(command):
            violations.append("Command requires admin privileges")

        return PolicyResult(
            allowed=len(violations) == 0,
            reason="Local policy evaluation",
            violations=violations if violations else None,
            metadata={"source": "local", "checks_performed": 4},
        )

    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command is inherently dangerous."""
        dangerous = [
            "rm -rf /",
            "mkfs.",
            "dd if=/dev/zero",
            ":(){ :|:& };:",  # Fork bomb
            "> /dev/sda",
            "mv / /dev/null",
        ]
        cmd_lower = command.lower()
        return any(d in cmd_lower for d in dangerous)

    def _has_destructive_flags(self, command: str) -> bool:
        """Check for destructive command flags."""
        destructive_patterns = [
            "rm -rf",
            "rm -f /",
            "rm --no-preserve-root",
        ]
        cmd_lower = command.lower()
        return any(p in cmd_lower for p in destructive_patterns)

    def _accesses_sensitive_paths(self, command: str) -> bool:
        """Check if command accesses sensitive system paths."""
        sensitive_paths = [
            "/etc/shadow",
            "/etc/passwd",
            "/etc/ssh",
            "/root/",
            "/var/log",
        ]
        return any(path in command for path in sensitive_paths)

    def _requires_admin(self, command: str) -> bool:
        """Check if command typically requires admin privileges."""
        admin_commands = [
            "useradd", "userdel", "usermod",
            "groupadd", "groupdel", "groupmod",
            "fdisk", "mkfs", "mount", "umount",
            "systemctl", "service",
            "apt-get", "yum", "dnf", "pacman",
        ]
        cmd_parts = command.split()
        if not cmd_parts:
            return False
        base_cmd = cmd_parts[0].split("/")[-1]
        return base_cmd in admin_commands

    def reload_policies(self) -> None:
        """Reload policies from disk."""
        self._policies.clear()
        self._load_policies()
        logger.info("Policies reloaded")

    def get_loaded_policies(self) -> list[str]:
        """Get list of loaded policy names."""
        return list(self._policies.keys())
