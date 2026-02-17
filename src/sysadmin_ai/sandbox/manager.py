"""Sandbox management for isolated command execution."""

from __future__ import annotations

import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class SandboxConfig:
    """Configuration for a sandbox environment."""
    
    # User isolation
    user_id: str | None = None
    namespace: str = "default"
    
    # Resource limits
    cpu_limit: str = "1.0"
    memory_limit: str = "512m"
    disk_limit: str = "1g"
    
    # Network
    network_mode: str = "none"  # none, bridge, host
    allowed_hosts: list[str] = field(default_factory=list)
    
    # Filesystem
    read_only_paths: list[str] = field(default_factory=list)
    writable_paths: list[str] = field(default_factory=list)
    
    # Timeouts
    command_timeout: int = 30
    max_session_duration: int = 3600  # 1 hour
    
    # Security
    drop_capabilities: bool = True
    no_new_privileges: bool = True
    seccomp_profile: str | None = None


@dataclass
class Sandbox:
    """Represents a sandboxed execution environment."""
    
    id: str
    config: SandboxConfig
    created_at: float = field(default_factory=lambda: __import__("time").time())
    last_activity: float = field(default_factory=lambda: __import__("time").time())
    command_count: int = 0
    
    # Runtime state
    _temp_dir: Path | None = None
    _docker_container: str | None = None
    _k8s_pod: str | None = None


class SandboxManager:
    """Manages sandboxed execution environments."""
    
    def __init__(self, backend: str = "auto") -> None:
        """Initialize sandbox manager.
        
        Args:
            backend: Sandbox backend - "docker", "k8s", "chroot", or "auto"
        """
        self.backend = self._detect_backend(backend)
        self._sandboxes: dict[str, Sandbox] = {}
        self._base_temp_dir = Path(tempfile.gettempdir()) / "sysadmin-ai-sandboxes"
        self._base_temp_dir.mkdir(parents=True, exist_ok=True)
    
    def _detect_backend(self, backend: str) -> str:
        """Detect available sandbox backend."""
        if backend != "auto":
            return backend
        
        # Check for Kubernetes
        if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount"):
            return "k8s"
        
        # Check for Docker
        try:
            subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
                check=True,
            )
            return "docker"
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Fallback to chroot (limited isolation)
        return "chroot"
    
    def create_sandbox(
        self,
        user_id: str | None = None,
        config: SandboxConfig | None = None,
    ) -> Sandbox:
        """Create a new sandbox.
        
        Args:
            user_id: User identifier for isolation
            config: Sandbox configuration
        
        Returns:
            Created sandbox instance
        """
        config = config or SandboxConfig()
        config.user_id = user_id or str(uuid.uuid4())
        
        sandbox_id = f"sandbox-{config.user_id}-{uuid.uuid4().hex[:8]}"
        sandbox = Sandbox(id=sandbox_id, config=config)
        
        # Create sandbox environment based on backend
        if self.backend == "docker":
            self._create_docker_sandbox(sandbox)
        elif self.backend == "k8s":
            self._create_k8s_sandbox(sandbox)
        elif self.backend == "chroot":
            self._create_chroot_sandbox(sandbox)
        
        self._sandboxes[sandbox_id] = sandbox
        return sandbox
    
    def _create_docker_sandbox(self, sandbox: Sandbox) -> None:
        """Create Docker-based sandbox."""
        config = sandbox.config
        
        # Create temp directory for sandbox
        temp_dir = self._base_temp_dir / sandbox.id
        temp_dir.mkdir(parents=True, exist_ok=True)
        sandbox._temp_dir = temp_dir
        
        # Build Docker run command
        cmd = [
            "docker", "run", "-d",
            "--name", sandbox.id,
            "--rm",
            "--network", config.network_mode,
            "--cpus", config.cpu_limit,
            "--memory", config.memory_limit,
            "--pids-limit", "100",
            "--security-opt", "no-new-privileges:true",
        ]
        
        if config.drop_capabilities:
            cmd.extend(["--cap-drop", "ALL"])
        
        # Mount temp directory
        cmd.extend(["-v", f"{temp_dir}:/workspace"])
        
        # Add read-only mounts
        for path in config.read_only_paths:
            if Path(path).exists():
                cmd.extend(["-v", f"{path}:{path}:ro"])
        
        # Use ubuntu as base image
        cmd.append("ubuntu:22.04")
        cmd.extend(["sleep", "3600"])  # Keep container running
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            sandbox._docker_container = result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create Docker sandbox: {e.stderr}") from e
    
    def _create_k8s_sandbox(self, sandbox: Sandbox) -> None:
        """Create Kubernetes-based sandbox."""
        # In a real implementation, this would create a pod via K8s API
        # For now, we'll create a pod name and let the executor handle it
        sandbox._k8s_pod = sandbox.id
    
    def _create_chroot_sandbox(self, sandbox: Sandbox) -> None:
        """Create chroot-based sandbox (limited isolation)."""
        temp_dir = self._base_temp_dir / sandbox.id
        temp_dir.mkdir(parents=True, exist_ok=True)
        sandbox._temp_dir = temp_dir
        
        # Create minimal filesystem structure
        for subdir in ["bin", "lib", "lib64", "usr", "workspace"]:
            (temp_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    def execute_in_sandbox(
        self,
        sandbox_id: str,
        command: str,
        cwd: str | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Execute a command in a sandbox.
        
        Args:
            sandbox_id: Sandbox identifier
            command: Command to execute
            cwd: Working directory (relative to sandbox)
            timeout: Command timeout
        
        Returns:
            Execution result
        """
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            raise ValueError(f"Sandbox {sandbox_id} not found")
        
        timeout = timeout or sandbox.config.command_timeout
        sandbox.last_activity = __import__("time").time()
        sandbox.command_count += 1
        
        if self.backend == "docker":
            return self._execute_docker(sandbox, command, cwd, timeout)
        elif self.backend == "k8s":
            return self._execute_k8s(sandbox, command, cwd, timeout)
        else:
            return self._execute_chroot(sandbox, command, cwd, timeout)
    
    def _execute_docker(
        self,
        sandbox: Sandbox,
        command: str,
        cwd: str | None,
        timeout: int,
    ) -> dict[str, Any]:
        """Execute in Docker container."""
        workdir = cwd or "/workspace"
        
        cmd = [
            "docker", "exec",
            "-w", workdir,
            sandbox._docker_container,
            "sh", "-c", command,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "exit_code": -1,
                "timed_out": True,
            }
    
    def _execute_k8s(
        self,
        sandbox: Sandbox,
        command: str,
        cwd: str | None,
        timeout: int,
    ) -> dict[str, Any]:
        """Execute in Kubernetes pod."""
        # This would use the Kubernetes API in a full implementation
        # For now, return a placeholder
        return {
            "stdout": "",
            "stderr": "K8s execution not fully implemented",
            "exit_code": 1,
            "timed_out": False,
        }
    
    def _execute_chroot(
        self,
        sandbox: Sandbox,
        command: str,
        cwd: str | None,
        timeout: int,
    ) -> dict[str, Any]:
        """Execute in chroot environment."""
        # Chroot execution requires root privileges
        # This is a simplified implementation
        workdir = sandbox._temp_dir / (cwd or "workspace")
        workdir.mkdir(parents=True, exist_ok=True)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "exit_code": -1,
                "timed_out": True,
            }
    
    def destroy_sandbox(self, sandbox_id: str) -> None:
        """Destroy a sandbox and clean up resources."""
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            return
        
        # Clean up based on backend
        if self.backend == "docker" and sandbox._docker_container:
            try:
                subprocess.run(
                    ["docker", "rm", "-f", sandbox._docker_container],
                    capture_output=True,
                    timeout=30,
                )
            except subprocess.SubprocessError:
                pass
        
        elif self.backend == "k8s" and sandbox._k8s_pod:
            # Would delete K8s pod via API
            pass
        
        # Clean up temp directory
        if sandbox._temp_dir and sandbox._temp_dir.exists():
            import shutil
            shutil.rmtree(sandbox._temp_dir, ignore_errors=True)
        
        del self._sandboxes[sandbox_id]
    
    def list_sandboxes(self) -> list[Sandbox]:
        """List all active sandboxes."""
        return list(self._sandboxes.values())
    
    def get_sandbox(self, sandbox_id: str) -> Sandbox | None:
        """Get a sandbox by ID."""
        return self._sandboxes.get(sandbox_id)
    
    def cleanup_expired(self, max_idle_seconds: int = 3600) -> int:
        """Clean up sandboxes that have been idle too long.
        
        Returns:
            Number of sandboxes cleaned up
        """
        import time
        
        current_time = time.time()
        expired = [
            sid for sid, sandbox in self._sandboxes.items()
            if current_time - sandbox.last_activity > max_idle_seconds
        ]
        
        for sid in expired:
            self.destroy_sandbox(sid)
        
        return len(expired)
    
    def shutdown(self) -> None:
        """Shutdown all sandboxes and clean up."""
        for sandbox_id in list(self._sandboxes.keys()):
            self.destroy_sandbox(sandbox_id)
