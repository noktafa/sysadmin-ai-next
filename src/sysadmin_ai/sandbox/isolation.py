"""Multi-user session isolation with sandbox namespaces."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a sandboxed execution."""

    success: bool
    output: str | None = None
    error: str | None = None
    returncode: int | None = None
    sandbox_id: str | None = None
    execution_time_ms: float | None = None


@dataclass
class SessionRecord:
    """Record of a session execution."""

    command: str
    timestamp: str
    user: str
    output: str | None = None
    success: bool = True


class SessionIsolation:
    """Provides per-user sandbox namespaces for command execution."""

    def __init__(
        self,
        user_id: str,
        sandbox_root: str | Path | None = None,
        enable_network_isolation: bool = True,
        enable_filesystem_isolation: bool = True,
    ):
        self.user_id = user_id
        self.sandbox_id = self._generate_sandbox_id(user_id)
        self.enable_network_isolation = enable_network_isolation
        self.enable_filesystem_isolation = enable_filesystem_isolation
        
        # Set up sandbox directory
        if sandbox_root:
            self.sandbox_root = Path(sandbox_root)
        else:
            self.sandbox_root = Path(tempfile.gettempdir()) / "sysadmin-ai" / self.sandbox_id
        
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        
        # Session history
        self._history: list[SessionRecord] = []
        
        logger.info(f"SessionIsolation initialized for user {user_id} in {self.sandbox_root}")

    def _generate_sandbox_id(self, user_id: str) -> str:
        """Generate a unique sandbox ID for the user."""
        hash_input = f"{user_id}:{datetime.now().strftime('%Y%m%d')}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    async def execute(self, command: str, timeout: float = 60.0) -> ExecutionResult:
        """Execute a command in the sandboxed environment.

        Args:
            command: The command to execute
            timeout: Maximum execution time in seconds

        Returns:
            Execution result
        """
        start_time = datetime.now()
        
        # Prepare the sandboxed command
        sandboxed_cmd = self._prepare_command(command)
        
        try:
            # Create subprocess with resource limits
            proc = await asyncio.create_subprocess_shell(
                sandboxed_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.sandbox_root),
                # Limit environment
                env=self._get_sandbox_env(),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                
                # Record failed execution
                self._record_execution(command, "", False)
                
                return ExecutionResult(
                    success=False,
                    error=f"Command timed out after {timeout} seconds",
                    returncode=-1,
                    sandbox_id=self.sandbox_id,
                )

            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            output = stdout.decode() if stdout else None
            error = stderr.decode() if stderr else None
            success = proc.returncode == 0

            # Record execution
            self._record_execution(command, output or "", success)

            return ExecutionResult(
                success=success,
                output=output,
                error=error,
                returncode=proc.returncode,
                sandbox_id=self.sandbox_id,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            logger.exception("Sandbox execution failed")
            self._record_execution(command, str(e), False)
            return ExecutionResult(
                success=False,
                error=str(e),
                sandbox_id=self.sandbox_id,
            )

    def _prepare_command(self, command: str) -> str:
        """Prepare command for sandboxed execution.

        Args:
            command: Original command

        Returns:
            Sandboxed command
        """
        # Start with any necessary sandboxing prefixes
        parts = []
        
        # Add network isolation if enabled
        if self.enable_network_isolation:
            # Use unshare to create network namespace
            parts.append("unshare -n")
        
        # Add filesystem isolation if enabled
        if self.enable_filesystem_isolation:
            # Use chroot or similar for filesystem isolation
            # Note: This is simplified; real implementation would use proper containerization
            pass

        # Add resource limits using ulimit
        parts.extend([
            "ulimit -t 30",  # CPU time limit
            "ulimit -v 1048576",  # Virtual memory limit (1GB)
            "ulimit -f 102400",  # File size limit (100MB)
            "ulimit -n 1024",  # Max open files
        ])

        # Add the actual command
        parts.append(command)

        return "; ".join(parts)

    def _get_sandbox_env(self) -> dict[str, str]:
        """Get sanitized environment variables for sandbox.

        Returns:
            Dictionary of environment variables
        """
        # Start with minimal environment
        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": str(self.sandbox_root),
            "USER": self.user_id,
            "SANDBOX_ID": self.sandbox_id,
            "LANG": "C.UTF-8",
            "TERM": "dumb",
        }
        
        # Add some safe variables if they exist
        safe_vars = ["TZ", "LC_ALL", "LC_CTYPE"]
        for var in safe_vars:
            if var in os.environ:
                env[var] = os.environ[var]

        return env

    def _record_execution(self, command: str, output: str, success: bool) -> None:
        """Record execution in session history."""
        record = SessionRecord(
            command=command,
            timestamp=datetime.now().isoformat(),
            user=self.user_id,
            output=output[:1000] if output else None,  # Limit stored output
            success=success,
        )
        self._history.append(record)

    def get_history(self) -> list[SessionRecord]:
        """Get session execution history.

        Returns:
            List of session records
        """
        return self._history.copy()

    def get_sandbox_info(self) -> dict[str, Any]:
        """Get information about the sandbox.

        Returns:
            Sandbox information dictionary
        """
        return {
            "sandbox_id": self.sandbox_id,
            "user_id": self.user_id,
            "root_directory": str(self.sandbox_root),
            "network_isolation": self.enable_network_isolation,
            "filesystem_isolation": self.enable_filesystem_isolation,
            "command_count": len(self._history),
            "created_at": self.sandbox_root.stat().st_ctime if self.sandbox_root.exists() else None,
        }

    def cleanup(self) -> None:
        """Clean up sandbox resources."""
        try:
            if self.sandbox_root.exists():
                import shutil
                shutil.rmtree(self.sandbox_root, ignore_errors=True)
                logger.info(f"Cleaned up sandbox: {self.sandbox_root}")
        except Exception as e:
            logger.error(f"Failed to cleanup sandbox: {e}")

    def __enter__(self) -> SessionIsolation:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.cleanup()
