"""Fuzzy command recovery - suggest safe alternatives when commands are blocked."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class CommandSuggestion:
    """A suggested alternative command."""
    
    original: str
    suggestion: str
    reason: str
    confidence: float  # 0.0 to 1.0
    safe: bool  # Whether this suggestion is considered safe


class RecoveryEngine:
    """Engine for recovering from blocked commands with suggestions."""
    
    def __init__(self) -> None:
        """Initialize recovery engine."""
        self._alternatives: dict[str, list[dict[str, Any]]] = {
            "rm_rf": [
                {
                    "pattern": r"rm\s+-rf\s+/",
                    "suggestion": "rm -rf /path/to/specific/directory",
                    "reason": "Never run rm -rf on root. Specify the exact directory.",
                },
                {
                    "pattern": r"rm\s+-rf\s+~",
                    "suggestion": "rm -rf ~/specific_directory",
                    "reason": "Specify exact subdirectory instead of home.",
                },
            ],
            "curl_bash": [
                {
                    "pattern": r"curl\s+.*\|\s*bash",
                    "suggestion": "curl -o script.sh URL && cat script.sh && bash script.sh",
                    "reason": "Download and review before executing.",
                },
                {
                    "pattern": r"curl\s+.*\|\s*sh",
                    "suggestion": "curl -o script.sh URL && cat script.sh && sh script.sh",
                    "reason": "Download and review before executing.",
                },
            ],
            "wget_pipe": [
                {
                    "pattern": r"wget\s+.*-\s*\|\s*(ba)?sh",
                    "suggestion": "wget -O script.sh URL && cat script.sh && bash script.sh",
                    "reason": "Download and review before executing.",
                },
            ],
            "chmod_dangerous": [
                {
                    "pattern": r"chmod\s+777\s+/",
                    "suggestion": "chmod 755 /specific/path",
                    "reason": "777 on root is dangerous. Use more restrictive permissions.",
                },
                {
                    "pattern": r"chmod\s+-R\s+777\s+/",
                    "suggestion": "chmod -R 755 /specific/path",
                    "reason": "Recursive 777 is dangerous. Use more restrictive permissions.",
                },
            ],
            "service_restart": [
                {
                    "pattern": r"systemctl\s+restart\s+.*",
                    "suggestion": "systemctl status <service> && systemctl restart <service>",
                    "reason": "Check service status before restarting.",
                },
            ],
            "package_remove": [
                {
                    "pattern": r"(apt|yum|dnf)\s+remove\s+.*",
                    "suggestion": "apt list --installed | grep <package> && apt remove <package>",
                    "reason": "Verify package exists and check dependencies first.",
                },
            ],
            "docker_prune": [
                {
                    "pattern": r"docker\s+system\s+prune\s+-f",
                    "suggestion": "docker system prune --dry-run",
                    "reason": "Preview what will be removed before pruning.",
                },
            ],
            "kubectl_delete": [
                {
                    "pattern": r"kubectl\s+delete\s+.*",
                    "suggestion": "kubectl get <resource> && kubectl delete <resource> --dry-run=client",
                    "reason": "Verify resources exist and dry-run before deleting.",
                },
            ],
            "dd_disk": [
                {
                    "pattern": r"dd\s+.*of=/dev/[sh]d",
                    "suggestion": "lsblk && dd if=/path/to/image of=/dev/sdX bs=4M status=progress",
                    "reason": "Verify target device with lsblk before writing.",
                },
            ],
        }
        
        # Common safe patterns that might be flagged
        self._safe_patterns: dict[str, str] = {
            r"rm\s+-rf\s+/tmp/": "Safe: removing /tmp contents is generally OK",
            r"rm\s+-rf\s+/var/tmp/": "Safe: removing /var/tmp contents is generally OK",
            r"find\s+/tmp\s+-type\s+f\s+-delete": "Safe: cleaning temp files",
        }
    
    def suggest_alternatives(self, command: str) -> list[CommandSuggestion]:
        """Suggest alternatives for a blocked command.
        
        Args:
            command: The blocked command
        
        Returns:
            List of command suggestions
        """
        suggestions = []
        
        # Check if it's actually a safe pattern
        for pattern, reason in self._safe_patterns.items():
            if re.search(pattern, command, re.IGNORECASE):
                suggestions.append(CommandSuggestion(
                    original=command,
                    suggestion=command,
                    reason=reason,
                    confidence=0.9,
                    safe=True,
                ))
                return suggestions
        
        # Check alternative patterns
        for category, alternatives in self._alternatives.items():
            for alt in alternatives:
                if re.search(alt["pattern"], command, re.IGNORECASE):
                    suggestion = self._customize_suggestion(command, alt)
                    suggestions.append(CommandSuggestion(
                        original=command,
                        suggestion=suggestion,
                        reason=alt["reason"],
                        confidence=0.8,
                        safe=True,
                    ))
        
        # If no specific match, try fuzzy matching
        if not suggestions:
            fuzzy_suggestions = self._fuzzy_suggest(command)
            suggestions.extend(fuzzy_suggestions)
        
        return sorted(suggestions, key=lambda s: s.confidence, reverse=True)
    
    def _customize_suggestion(self, original: str, alternative: dict[str, Any]) -> str:
        """Customize a suggestion based on the original command."""
        suggestion = alternative["suggestion"]
        
        # Try to extract specific values from original command
        # This is a simplified implementation
        
        # Extract service name for systemctl commands
        if "systemctl" in original:
            match = re.search(r"systemctl\s+\w+\s+(\S+)", original)
            if match:
                service = match.group(1)
                suggestion = suggestion.replace("<service>", service)
        
        # Extract package name for package commands
        if any(cmd in original for cmd in ["apt", "yum", "dnf"]):
            parts = original.split()
            if len(parts) >= 3:
                package = parts[-1]
                suggestion = suggestion.replace("<package>", package)
        
        # Extract resource for kubectl
        if "kubectl" in original:
            match = re.search(r"kubectl\s+\w+\s+(\S+)\s+(\S+)", original)
            if match:
                resource = match.group(1)
                suggestion = suggestion.replace("<resource>", resource)
        
        return suggestion
    
    def _fuzzy_suggest(self, command: str) -> list[CommandSuggestion]:
        """Use fuzzy matching to suggest alternatives."""
        suggestions = []
        
        try:
            from thefuzz import fuzz, process
            
            # Build list of all alternative suggestions
            all_alternatives = []
            for category, alternatives in self._alternatives.items():
                for alt in alternatives:
                    all_alternatives.append((alt["pattern"], alt["suggestion"], alt["reason"]))
            
            # Find best matches
            for pattern, suggestion, reason in all_alternatives:
                # Simple string similarity
                similarity = fuzz.partial_ratio(command.lower(), pattern.lower())
                if similarity > 60:  # Threshold
                    suggestions.append(CommandSuggestion(
                        original=command,
                        suggestion=suggestion,
                        reason=f"{reason} (fuzzy match: {similarity}%)",
                        confidence=similarity / 100.0,
                        safe=True,
                    ))
        
        except ImportError:
            # thefuzz not available, skip fuzzy matching
            pass
        
        return suggestions
    
    def explain_block(self, command: str, rule_name: str | None = None) -> str:
        """Generate an explanation for why a command was blocked.
        
        Args:
            command: The blocked command
            rule_name: Name of the rule that blocked it
        
        Returns:
            Human-readable explanation
        """
        explanations = {
            "rm_rf_root": "This command would recursively delete files from the root directory, which could destroy the entire system.",
            "mkfs_block": "This command formats filesystems, which would destroy all data on the target device.",
            "dd_to_disk": "Direct disk writes can corrupt the operating system or destroy data.",
            "shadow_access": "Password files contain sensitive credential information.",
            "ssh_key_access": "SSH private keys grant access to remote systems.",
            "curl_pipe_bash": "Piping curl directly to a shell executes code without review, which is a common attack vector.",
            "kubectl_delete": "Force-deleting Kubernetes resources can cause service disruptions.",
            "kubectl_secret_access": "Kubernetes secrets contain sensitive data like passwords and API keys.",
        }
        
        if rule_name and rule_name in explanations:
            return explanations[rule_name]
        
        # Generic explanation
        return f"The command '{command[:50]}...' matches a security policy that prevents potentially dangerous operations."
    
    def get_learning_suggestion(self, command: str, output: str) -> str | None:
        """Suggest learning resources based on the command type.
        
        Args:
            command: The command that was run
            output: Command output
        
        Returns:
            Learning suggestion or None
        """
        if "docker" in command.lower():
            return "Learn more about Docker security: https://docs.docker.com/engine/security/"
        
        if "kubectl" in command.lower():
            return "Learn more about Kubernetes security: https://kubernetes.io/docs/concepts/security/"
        
        if any(cmd in command.lower() for cmd in ["iptables", "ufw", "firewalld"]):
            return "Learn more about Linux firewall configuration and security best practices."
        
        if "chmod" in command.lower():
            return "Learn about Linux permissions: https://chmod-calculator.com/"
        
        return None
