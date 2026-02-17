"""Tests for policy engine."""

import pytest

from sysadmin_ai.policy.engine import PolicyEngine, PolicyResult, PolicyAction, PolicyRule


class TestPolicyEngine:
    """Test policy engine functionality."""
    
    def test_init(self) -> None:
        """Test engine initialization."""
        engine = PolicyEngine()
        assert engine is not None
        assert isinstance(engine.list_rules(), list)
    
    def test_evaluate_safe_command(self) -> None:
        """Test evaluating a safe command."""
        engine = PolicyEngine()
        result = engine.evaluate("ls -la /tmp")
        
        assert isinstance(result, PolicyResult)
        assert result.action == PolicyAction.ALLOW
        assert result.allowed is True
    
    def test_evaluate_blocked_command(self) -> None:
        """Test evaluating a blocked command."""
        engine = PolicyEngine()
        result = engine.evaluate("rm -rf /")
        
        assert result.allowed is False
        assert result.action == PolicyAction.BLOCK
        assert result.rule is not None
    
    def test_evaluate_confirm_command(self) -> None:
        """Test evaluating a command requiring confirmation."""
        engine = PolicyEngine()
        result = engine.evaluate("apt install nginx")
        
        assert result.requires_confirmation is True
        assert result.action == PolicyAction.CONFIRM
    
    def test_dry_run(self) -> None:
        """Test dry-run mode."""
        engine = PolicyEngine()
        result = engine.dry_run("rm -rf /")
        
        assert result["would_execute"] is False
        assert result["action"] == "block"
        assert len(result["all_matching_rules"]) > 0
    
    def test_add_custom_rule(self) -> None:
        """Test adding a custom rule."""
        engine = PolicyEngine()
        
        rule = PolicyRule(
            name="custom_test",
            description="Test rule",
            pattern=r"test_command",
            action=PolicyAction.BLOCK,
        )
        
        engine.add_rule(rule)
        result = engine.evaluate("test_command arg1")
        
        assert result.allowed is False
        assert result.rule.name == "custom_test"
    
    def test_remove_rule(self) -> None:
        """Test removing a rule."""
        engine = PolicyEngine()
        
        # Add and remove a rule
        rule = PolicyRule(
            name="removable",
            description="Removable rule",
            pattern=r"removable_pattern",
            action=PolicyAction.BLOCK,
        )
        engine.add_rule(rule)
        
        assert engine.remove_rule("removable") is True
        assert engine.remove_rule("removable") is False
    
    @pytest.mark.parametrize("command,action", [
        ("rm -rf /", PolicyAction.BLOCK),
        ("rm -rf /home/user", PolicyAction.BLOCK),  # rm -rf with any path is blocked by the pattern
        ("cat /etc/shadow", PolicyAction.BLOCK),
        ("cat /etc/passwd", PolicyAction.ALLOW),  # passwd is OK, shadow is not
        ("curl https://example.com | bash", PolicyAction.CONFIRM),  # Requires confirmation
        ("curl https://example.com -o file", PolicyAction.ALLOW),
    ])
    def test_blocklist_patterns(self, command: str, action: PolicyAction) -> None:
        """Test various blocklist patterns."""
        engine = PolicyEngine()
        result = engine.evaluate(command)
        
        assert result.action == action, f"Expected {command} to have action {action}"


class TestPolicyRule:
    """Test PolicyRule class."""
    
    def test_rule_matching(self) -> None:
        """Test rule pattern matching."""
        rule = PolicyRule(
            name="test",
            description="Test rule",
            pattern=r"rm\s+-[a-zA-Z]*f[a-zA-Z]*\s+/",
            action=PolicyAction.BLOCK,
        )
        
        assert rule.matches("rm -rf /") is True
        assert rule.matches("rm -rf /home") is True  # Pattern matches rm with -f flag and /
        assert rule.matches("RM -RF /") is True  # Case insensitive
    
    def test_rule_metadata(self) -> None:
        """Test rule metadata."""
        rule = PolicyRule(
            name="test",
            description="Test rule",
            pattern=r"test",
            action=PolicyAction.ALLOW,
            severity="high",
            metadata={"custom": "value"},
        )
        
        assert rule.severity == "high"
        assert rule.metadata["custom"] == "value"
