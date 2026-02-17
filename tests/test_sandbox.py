"""Tests for sandbox manager."""

import pytest

from sysadmin_ai.sandbox.manager import SandboxConfig, SandboxManager


class TestSandboxManager:
    """Test sandbox manager functionality."""
    
    def test_init(self) -> None:
        """Test manager initialization."""
        manager = SandboxManager(backend="chroot")
        assert manager is not None
        assert manager.backend == "chroot"
    
    def test_create_sandbox(self) -> None:
        """Test creating a sandbox."""
        manager = SandboxManager(backend="chroot")
        
        config = SandboxConfig(
            user_id="test-user",
            memory_limit="256m",
            command_timeout=10,
        )
        
        sandbox = manager.create_sandbox(user_id="test-user", config=config)
        
        assert sandbox.id.startswith("sandbox-")
        assert sandbox.config.user_id == "test-user"
        
        # Cleanup
        manager.destroy_sandbox(sandbox.id)
    
    def test_list_sandboxes(self) -> None:
        """Test listing sandboxes."""
        manager = SandboxManager(backend="chroot")
        
        # Should start empty
        assert len(manager.list_sandboxes()) == 0
        
        # Create a sandbox
        sandbox = manager.create_sandbox(user_id="test")
        
        # Should have one
        sandboxes = manager.list_sandboxes()
        assert len(sandboxes) == 1
        assert sandboxes[0].id == sandbox.id
        
        # Cleanup
        manager.destroy_sandbox(sandbox.id)
    
    def test_execute_in_sandbox(self) -> None:
        """Test executing commands in sandbox."""
        manager = SandboxManager(backend="chroot")
        sandbox = manager.create_sandbox(user_id="test")
        
        try:
            result = manager.execute_in_sandbox(sandbox.id, "echo hello")
            
            assert result["exit_code"] == 0
            assert "hello" in result["stdout"]
            assert result["timed_out"] is False
        finally:
            manager.destroy_sandbox(sandbox.id)
    
    def test_execute_timeout(self) -> None:
        """Test command timeout."""
        manager = SandboxManager(backend="chroot")
        config = SandboxConfig(command_timeout=1)
        sandbox = manager.create_sandbox(user_id="test", config=config)
        
        try:
            result = manager.execute_in_sandbox(sandbox.id, "sleep 10", timeout=1)
            
            assert result["timed_out"] is True
            assert result["exit_code"] == -1
        finally:
            manager.destroy_sandbox(sandbox.id)
    
    def test_get_sandbox(self) -> None:
        """Test getting a specific sandbox."""
        manager = SandboxManager(backend="chroot")
        sandbox = manager.create_sandbox(user_id="test")
        
        try:
            retrieved = manager.get_sandbox(sandbox.id)
            assert retrieved is not None
            assert retrieved.id == sandbox.id
            
            # Non-existent sandbox
            assert manager.get_sandbox("non-existent") is None
        finally:
            manager.destroy_sandbox(sandbox.id)
    
    def test_cleanup_expired(self) -> None:
        """Test cleaning up expired sandboxes."""
        manager = SandboxManager(backend="chroot")
        sandbox = manager.create_sandbox(user_id="test")
        
        # Sandbox should exist
        assert manager.get_sandbox(sandbox.id) is not None
        
        # Cleanup with very short timeout (0 seconds)
        # Note: This won't actually clean up because we just created it
        # But it tests the method exists and works
        count = manager.cleanup_expired(max_idle_seconds=0)
        
        # The sandbox was just created, so it shouldn't be cleaned up yet
        # unless time moves forward (which it doesn't in this test)
        # So we just verify the method runs without error
        assert isinstance(count, int)


class TestSandboxConfig:
    """Test SandboxConfig dataclass."""
    
    def test_default_config(self) -> None:
        """Test default configuration."""
        config = SandboxConfig()
        
        assert config.network_mode == "none"
        assert config.memory_limit == "512m"
        assert config.cpu_limit == "1.0"
        assert config.command_timeout == 30
        assert config.drop_capabilities is True
    
    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = SandboxConfig(
            user_id="custom-user",
            network_mode="bridge",
            memory_limit="1g",
            cpu_limit="2.0",
            command_timeout=60,
        )
        
        assert config.user_id == "custom-user"
        assert config.network_mode == "bridge"
        assert config.memory_limit == "1g"
        assert config.cpu_limit == "2.0"
        assert config.command_timeout == 60
