"""Tests for playbook generator."""

import pytest

from sysadmin_ai.playbooks.generator import (
    PlaybookGenerator,
    Session,
    SessionCommand,
)


class TestPlaybookGenerator:
    """Test playbook generator functionality."""
    
    @pytest.fixture
    def sample_session(self) -> Session:
        """Create a sample session for testing."""
        import time
        
        return Session(
            session_id="test-session",
            commands=[
                SessionCommand(
                    command="apt install nginx",
                    output="Reading package lists...",
                    exit_code=0,
                    timestamp=time.time(),
                ),
                SessionCommand(
                    command="systemctl enable nginx",
                    output="Created symlink...",
                    exit_code=0,
                    timestamp=time.time(),
                ),
                SessionCommand(
                    command="systemctl start nginx",
                    output="",
                    exit_code=0,
                    timestamp=time.time(),
                ),
            ],
        )
    
    def test_init(self) -> None:
        """Test generator initialization."""
        generator = PlaybookGenerator()
        assert generator is not None
    
    def test_generate_ansible(self, sample_session: Session) -> None:
        """Test Ansible playbook generation."""
        generator = PlaybookGenerator()
        result = generator.generate_ansible(sample_session)
        
        assert "playbook" in result
        assert "yaml" in result
        assert result["stats"]["total_commands"] == 3
        assert result["stats"]["converted_tasks"] >= 1
        
        # Check YAML content
        yaml_content = result["yaml"]
        assert "hosts: all" in yaml_content
        assert "become: true" in yaml_content or "become: True" in yaml_content
    
    def test_generate_terraform(self, sample_session: Session) -> None:
        """Test Terraform config generation."""
        generator = PlaybookGenerator()
        result = generator.generate_terraform(sample_session)
        
        assert "config" in result
        assert "hcl" in result
        assert "terraform" in result["config"]
    
    def test_generate_shell_script(self, sample_session: Session) -> None:
        """Test shell script generation."""
        generator = PlaybookGenerator()
        script = generator.generate_shell_script(sample_session)
        
        assert "#!/bin/bash" in script
        assert "apt install nginx" in script
        assert "systemctl enable nginx" in script
    
    def test_parse_apt_command(self) -> None:
        """Test parsing apt commands."""
        generator = PlaybookGenerator()
        
        import time
        cmd = SessionCommand(
            command="apt install nginx curl vim",
            output="",
            exit_code=0,
            timestamp=time.time(),
        )
        
        parsed = generator._parse_command(cmd)
        
        assert parsed is not None
        assert parsed["tool"] == "apt"
        assert parsed["action"] == "install"
        assert "nginx" in parsed["packages"]
        assert "curl" in parsed["packages"]
    
    def test_parse_systemctl_command(self) -> None:
        """Test parsing systemctl commands."""
        generator = PlaybookGenerator()
        
        import time
        cmd = SessionCommand(
            command="systemctl restart nginx",
            output="",
            exit_code=0,
            timestamp=time.time(),
        )
        
        parsed = generator._parse_command(cmd)
        
        assert parsed is not None
        assert parsed["tool"] == "systemctl"
        assert parsed["action"] == "restart"
        assert parsed["service"] == "nginx"
    
    def test_unknown_command(self) -> None:
        """Test handling unknown commands."""
        generator = PlaybookGenerator()
        
        import time
        cmd = SessionCommand(
            command="some_custom_command arg1 arg2",
            output="",
            exit_code=0,
            timestamp=time.time(),
        )
        
        parsed = generator._parse_command(cmd)
        
        assert parsed is not None
        assert parsed["tool"] == "some_custom_command"
        assert parsed["category"] == "unknown"
    
    def test_convert_to_ansible_task(self) -> None:
        """Test converting parsed command to Ansible task."""
        generator = PlaybookGenerator()
        
        import time
        parsed = {
            "tool": "apt",
            "action": "install",
            "packages": ["nginx"],
            "category": "package",
        }
        cmd = SessionCommand(
            command="apt install nginx",
            output="",
            exit_code=0,
            timestamp=time.time(),
        )
        
        task = generator._convert_to_ansible_task(parsed, cmd)
        
        assert task is not None
        assert "package" in task
        assert task["package"]["name"] == ["nginx"]
        assert task["package"]["state"] == "present"


class TestSession:
    """Test Session dataclass."""
    
    def test_session_creation(self) -> None:
        """Test creating a session."""
        session = Session(session_id="test")
        
        assert session.session_id == "test"
        assert len(session.commands) == 0
    
    def test_add_command(self) -> None:
        """Test adding commands to session."""
        import time
        
        session = Session(session_id="test")
        
        cmd = SessionCommand(
            command="ls -la",
            output="total 0",
            exit_code=0,
            timestamp=time.time(),
        )
        
        session.add_command(cmd)
        
        assert len(session.commands) == 1
        assert session.commands[0].command == "ls -la"
