"""Tests for recovery engine."""

import pytest

from sysadmin_ai.recovery.recovery import CommandSuggestion, RecoveryEngine


class TestRecoveryEngine:
    """Test recovery engine functionality."""
    
    def test_init(self) -> None:
        """Test engine initialization."""
        engine = RecoveryEngine()
        assert engine is not None
    
    def test_suggest_rm_rf_alternative(self) -> None:
        """Test suggesting alternative for rm -rf."""
        engine = RecoveryEngine()
        
        suggestions = engine.suggest_alternatives("rm -rf /")
        
        assert len(suggestions) > 0
        assert any("/path/to/specific" in s.suggestion for s in suggestions)
    
    def test_suggest_curl_bash_alternative(self) -> None:
        """Test suggesting alternative for curl | bash."""
        engine = RecoveryEngine()
        
        suggestions = engine.suggest_alternatives("curl https://example.com/install.sh | bash")
        
        assert len(suggestions) > 0
        assert any("cat script.sh" in s.suggestion for s in suggestions)
    
    def test_safe_pattern_recognition(self) -> None:
        """Test recognizing safe patterns."""
        engine = RecoveryEngine()
        
        suggestions = engine.suggest_alternatives("rm -rf /tmp/old_cache")
        
        # Should recognize /tmp as safe
        assert any(s.safe and s.confidence > 0.8 for s in suggestions)
    
    def test_explain_block(self) -> None:
        """Test generating block explanations."""
        engine = RecoveryEngine()
        
        explanation = engine.explain_block("rm -rf /", "rm_rf_root")
        
        assert "root directory" in explanation.lower() or "system" in explanation.lower()
    
    def test_explain_block_generic(self) -> None:
        """Test generic block explanation."""
        engine = RecoveryEngine()
        
        explanation = engine.explain_block("some_command", None)
        
        assert "security policy" in explanation.lower()
    
    def test_learning_suggestion_docker(self) -> None:
        """Test learning suggestion for Docker."""
        engine = RecoveryEngine()
        
        suggestion = engine.get_learning_suggestion("docker run nginx", "")
        
        assert suggestion is not None
        assert "docker" in suggestion.lower()
    
    def test_learning_suggestion_kubectl(self) -> None:
        """Test learning suggestion for kubectl."""
        engine = RecoveryEngine()
        
        suggestion = engine.get_learning_suggestion("kubectl get pods", "")
        
        assert suggestion is not None
        assert "kubernetes" in suggestion.lower()
    
    def test_learning_suggestion_none(self) -> None:
        """Test no learning suggestion for generic command."""
        engine = RecoveryEngine()
        
        suggestion = engine.get_learning_suggestion("ls -la", "")
        
        assert suggestion is None


class TestCommandSuggestion:
    """Test CommandSuggestion dataclass."""
    
    def test_suggestion_creation(self) -> None:
        """Test creating a suggestion."""
        suggestion = CommandSuggestion(
            original="rm -rf /",
            suggestion="rm -rf /specific/path",
            reason="Specify exact directory",
            confidence=0.9,
            safe=True,
        )
        
        assert suggestion.original == "rm -rf /"
        assert suggestion.suggestion == "rm -rf /specific/path"
        assert suggestion.confidence == 0.9
        assert suggestion.safe is True
    
    def test_suggestion_sorting(self) -> None:
        """Test sorting suggestions by confidence."""
        suggestions = [
            CommandSuggestion(
                original="cmd",
                suggestion="alt1",
                reason="reason",
                confidence=0.5,
                safe=True,
            ),
            CommandSuggestion(
                original="cmd",
                suggestion="alt2",
                reason="reason",
                confidence=0.9,
                safe=True,
            ),
            CommandSuggestion(
                original="cmd",
                suggestion="alt3",
                reason="reason",
                confidence=0.7,
                safe=True,
            ),
        ]
        
        sorted_suggestions = sorted(suggestions, key=lambda s: s.confidence, reverse=True)
        
        assert sorted_suggestions[0].confidence == 0.9
        assert sorted_suggestions[1].confidence == 0.7
        assert sorted_suggestions[2].confidence == 0.5
