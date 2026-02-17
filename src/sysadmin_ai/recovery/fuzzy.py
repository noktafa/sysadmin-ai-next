"""Fuzzy command recovery for suggesting safe alternatives."""

from __future__ import annotations

import logging
from typing import Any

from thefuzz import fuzz, process

logger = logging.getLogger(__name__)


class FuzzyRecovery:
    """Provides fuzzy matching and recovery suggestions for blocked commands."""

    # Safe alternatives for common dangerous commands
    COMMAND_ALTERNATIVES = {
        "rm -rf /": [
            "rm -rf /specific/path (specify actual path)",
            "trash-put /path (use trash instead)",
            "rm -ri /path (interactive mode)",
        ],
        "rm -rf": [
            "rm -ri /path (interactive recursive deletion)",
            "trash-put /path (move to trash)",
            "rm -rf /path --one-file-system (limit scope)",
        ],
        "dd if=/dev/zero": [
            "dd if=/dev/zero of=/path bs=1M count=100 (specify count limit)",
            "fio --name=test --filename=/path (use fio for testing)",
        ],
        "mkfs.": [
            "mkfs -n /dev/device (dry run first)",
            "lsblk (verify device before formatting)",
        ],
        "> /dev/sda": [
            "echo 'test' > /tmp/testfile (test on non-critical device)",
        ],
    }

    # Safe command patterns for common operations
    SAFE_PATTERNS = {
        "delete": [
            "trash-put {path}",
            "rm -i {path}",
            "gio trash {path}",
        ],
        "recursive_delete": [
            "find {path} -type f -delete (delete files only)",
            "find {path} -mtime +30 -delete (delete old files only)",
            "rm -ri {path} (interactive recursive)",
        ],
        "format": [
            "lsblk -f (list filesystems first)",
            "df -h (check mounted filesystems)",
            "mkfs -n {device} (dry run)",
        ],
        "user_management": [
            "useradd -n {user} (dry run)",
            "useradd --system {user} (system user)",
        ],
    }

    def __init__(self, threshold: int = 60) -> None:
        """Initialize fuzzy recovery.

        Args:
            threshold: Minimum similarity score (0-100) for matches
        """
        self.threshold = threshold

    async def suggest_alternatives(
        self,
        command: str,
        violations: list[str] | None = None,
    ) -> list[str]:
        """Suggest safe alternatives for a blocked command.

        Args:
            command: The blocked command
            violations: List of policy violations

        Returns:
            List of suggested alternatives
        """
        suggestions = []
        
        # Check for exact matches in alternatives
        cmd_lower = command.lower()
        for pattern, alts in self.COMMAND_ALTERNATIVES.items():
            if pattern in cmd_lower:
                suggestions.extend(alts)

        # Fuzzy match against dangerous patterns
        if not suggestions:
            suggestions = self._fuzzy_match_alternatives(command)

        # Generate contextual suggestions based on violations
        if violations:
            contextual = self._contextual_suggestions(command, violations)
            suggestions.extend(contextual)

        # Generate general safety suggestions
        general = self._general_suggestions(command)
        suggestions.extend(general)

        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)

        return unique_suggestions[:5]  # Limit to top 5

    def _fuzzy_match_alternatives(self, command: str) -> list[str]:
        """Find alternatives using fuzzy matching."""
        suggestions = []
        
        # Match against known dangerous patterns
        dangerous_patterns = list(self.COMMAND_ALTERNATIVES.keys())
        matches = process.extract(
            command.lower(),
            dangerous_patterns,
            scorer=fuzz.partial_ratio,
            limit=3,
        )
        
        for pattern, score, _ in matches:
            if score >= self.threshold:
                alts = self.COMMAND_ALTERNATIVES.get(pattern, [])
                suggestions.extend(alts)

        return suggestions

    def _contextual_suggestions(
        self,
        command: str,
        violations: list[str],
    ) -> list[str]:
        """Generate suggestions based on specific violations."""
        suggestions = []
        cmd_lower = command.lower()

        for violation in violations:
            v_lower = violation.lower()
            
            if "dangerous" in v_lower or "destructive" in v_lower:
                if "rm" in cmd_lower:
                    suggestions.extend([
                        "Use 'trash-put' instead of 'rm' for recoverable deletion",
                        "Add -i flag for interactive confirmation",
                        "Use find with -mtime to limit deletion to old files",
                    ])
                elif "dd" in cmd_lower:
                    suggestions.extend([
                        "Specify count= to limit bytes written",
                        "Use status=progress to monitor operation",
                    ])

            if "sensitive" in v_lower:
                suggestions.extend([
                    "Use sudo with specific user context",
                    "Consider using a configuration management tool",
                    "Backup files before modification",
                ])

            if "admin" in v_lower:
                suggestions.extend([
                    "Verify you have necessary permissions",
                    "Use sudo -u to run as specific user",
                    "Consider using a privileged container",
                ])

        return suggestions

    def _general_suggestions(self, command: str) -> list[str]:
        """Generate general safety suggestions."""
        suggestions = []
        
        # Parse command to extract components
        parts = command.split()
        if not parts:
            return suggestions

        base_cmd = parts[0]
        
        # Add echo prefix suggestion
        suggestions.append(f"Preview with: echo '{command}'")
        
        # Add dry-run suggestions for known commands
        dry_run_flags = {
            "rsync": "--dry-run",
            "apt": "--dry-run",
            "apt-get": "--dry-run",
            "yum": "--assumeno",
            "dnf": "--assumeno",
            "pacman": "--print",
            "make": "--dry-run",
            "useradd": "--dry-run",
            "usermod": "--dry-run",
        }
        
        if base_cmd in dry_run_flags:
            flag = dry_run_flags[base_cmd]
            suggestions.append(f"Test first: {base_cmd} {flag} {' '.join(parts[1:])}")

        # Suggest using --one-file-system for recursive operations
        if "-r" in command or "-R" in command or "--recursive" in command:
            if base_cmd in ["rm", "chown", "chmod"]:
                suggestions.append(
                    f"Limit scope: {base_cmd} --one-file-system {' '.join(parts[1:])}"
                )

        return suggestions

    def find_similar_safe_commands(
        self,
        command: str,
        safe_commands: list[str],
        limit: int = 3,
    ) -> list[tuple[str, int]]:
        """Find similar safe commands from a whitelist.

        Args:
            command: The command to match
            safe_commands: List of allowed commands
            limit: Maximum number of results

        Returns:
            List of (command, score) tuples
        """
        matches = process.extract(
            command,
            safe_commands,
            scorer=fuzz.ratio,
            limit=limit,
        )
        return [(match, score) for match, score, _ in matches if score >= self.threshold]

    def analyze_risk(self, command: str) -> dict[str, Any]:
        """Analyze the risk level of a command.

        Args:
            command: The command to analyze

        Returns:
            Risk analysis dictionary
        """
        risk_factors = []
        risk_score = 0
        
        cmd_lower = command.lower()
        
        # Check for high-risk patterns
        high_risk = ["rm -rf /", "mkfs", ":(){ :|:& };:", "> /dev/sda"]
        for pattern in high_risk:
            if pattern in cmd_lower:
                risk_score += 50
                risk_factors.append(f"Critical pattern: {pattern}")

        # Check for medium-risk patterns
        medium_risk = ["rm -rf", "rm -f", "dd if=/dev/zero", "mkfs."]
        for pattern in medium_risk:
            if pattern in cmd_lower:
                risk_score += 25
                risk_factors.append(f"High risk pattern: {pattern}")

        # Check for low-risk patterns
        low_risk = ["sudo", "su -", "passwd", "userdel"]
        for pattern in low_risk:
            if pattern in cmd_lower:
                risk_score += 10
                risk_factors.append(f"Elevated privilege: {pattern}")

        # Determine risk level
        if risk_score >= 50:
            level = "CRITICAL"
        elif risk_score >= 25:
            level = "HIGH"
        elif risk_score >= 10:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "level": level,
            "score": risk_score,
            "factors": risk_factors,
            "reversible": risk_score < 25 and "rm" not in cmd_lower,
        }
