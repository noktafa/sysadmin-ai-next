"""Built-in plugins for common operations."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sysadmin_ai.plugins.base import Plugin

logger = logging.getLogger(__name__)


class DockerPlugin(Plugin):
    """Plugin for Docker container operations."""

    name = "docker"
    version = "1.0.0"
    description = "Execute Docker commands safely"

    def can_handle(self, command: str) -> bool:
        """Check if command is a Docker command."""
        return command.strip().startswith("docker ")

    async def execute(self, command: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute Docker command with safety checks."""
        # Add safety checks for dangerous Docker commands
        dangerous = ["docker rm -f", "docker system prune", "docker rmi -f"]
        
        cmd_lower = command.lower()
        for pattern in dangerous:
            if pattern in cmd_lower:
                return {
                    "success": False,
                    "error": f"Potentially dangerous Docker command blocked: {pattern}",
                    "output": None,
                }

        # Execute the command
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            return {
                "success": proc.returncode == 0,
                "output": stdout.decode() if stdout else None,
                "error": stderr.decode() if stderr else None,
                "returncode": proc.returncode,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": None,
            }


class KubectlPlugin(Plugin):
    """Plugin for Kubernetes operations."""

    name = "kubectl"
    version = "1.0.0"
    description = "Execute kubectl commands with namespace safety"

    def can_handle(self, command: str) -> bool:
        """Check if command is a kubectl command."""
        return command.strip().startswith("kubectl ")

    async def execute(self, command: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute kubectl command with namespace validation."""
        # Check for protected namespaces
        protected = ["kube-system", "kube-public", "kube-node-lease"]
        
        for ns in protected:
            if f"-n {ns}" in command or f"--namespace={ns}" in command:
                # Check if user has permission
                perms = context.get("permissions", [])
                if "k8s-admin" not in perms:
                    return {
                        "success": False,
                        "error": f"Protected namespace '{ns}' requires k8s-admin permission",
                        "output": None,
                    }

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            return {
                "success": proc.returncode == 0,
                "output": stdout.decode() if stdout else None,
                "error": stderr.decode() if stderr else None,
                "returncode": proc.returncode,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": None,
            }


class GitPlugin(Plugin):
    """Plugin for Git operations."""

    name = "git"
    version = "1.0.0"
    description = "Execute Git commands with safety checks"

    def can_handle(self, command: str) -> bool:
        """Check if command is a git command."""
        return command.strip().startswith("git ")

    async def execute(self, command: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute git command with safety checks."""
        # Block dangerous git commands
        dangerous = [
            "git push --force", "git push -f",
            "git reset --hard", "git clean -fd",
        ]
        
        cmd_lower = command.lower()
        for pattern in dangerous:
            if pattern in cmd_lower:
                return {
                    "success": False,
                    "error": f"Destructive git command requires confirmation: {pattern}",
                    "output": None,
                    "requires_confirmation": True,
                }

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            return {
                "success": proc.returncode == 0,
                "output": stdout.decode() if stdout else None,
                "error": stderr.decode() if stderr else None,
                "returncode": proc.returncode,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": None,
            }
