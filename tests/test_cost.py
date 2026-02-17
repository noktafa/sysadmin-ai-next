"""Tests for cost tracking."""

import pytest

from sysadmin_ai.cost.tracker import CostTracker, TokenUsage, CostContext


class TestCostTracker:
    """Test cost tracking functionality."""
    
    def test_init(self) -> None:
        """Test tracker initialization."""
        tracker = CostTracker()
        assert tracker is not None
        assert tracker.enabled is True
        assert tracker.default_model == "gpt-3.5-turbo"
    
    def test_init_disabled(self) -> None:
        """Test disabled tracker."""
        tracker = CostTracker(enabled=False)
        assert tracker.enabled is False
    
    def test_token_usage_add(self) -> None:
        """Test adding token usage."""
        usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50)
        usage2 = TokenUsage(prompt_tokens=50, completion_tokens=25)
        
        usage1.add(usage2)
        
        assert usage1.prompt_tokens == 150
        assert usage1.completion_tokens == 75
        # total_tokens is calculated in post_init, so we check the sum
        assert usage1.prompt_tokens + usage1.completion_tokens == 225
    
    def test_calculate_cost(self) -> None:
        """Test cost calculation."""
        tracker = CostTracker()
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500)
        
        cost = tracker._calculate_cost(usage, "gpt-3.5-turbo")
        
        # gpt-3.5-turbo: input $0.0005/1K, output $0.0015/1K
        expected = (1000/1000 * 0.0005) + (500/1000 * 0.0015)
        assert cost == pytest.approx(expected, rel=1e-6)
    
    def test_calculate_cost_unknown_model(self) -> None:
        """Test cost calculation with unknown model."""
        tracker = CostTracker()
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500)
        
        # Should fall back to gpt-3.5-turbo pricing
        cost = tracker._calculate_cost(usage, "unknown-model")
        assert cost > 0
    
    def test_get_user_stats_empty(self) -> None:
        """Test user stats with no records."""
        tracker = CostTracker()
        stats = tracker.get_user_stats("testuser")
        
        assert stats["user_id"] == "testuser"
        assert stats["total_commands"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_cost_usd"] == 0.0
    
    def test_get_global_stats_empty(self) -> None:
        """Test global stats with no records."""
        tracker = CostTracker()
        stats = tracker.get_global_stats()
        
        assert stats["total_commands"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_cost_usd"] == 0.0
        assert stats["unique_users"] == 0
    
    def test_model_pricing_exists(self) -> None:
        """Test that model pricing is defined."""
        tracker = CostTracker()
        
        assert "gpt-4" in tracker.MODEL_PRICING
        assert "gpt-3.5-turbo" in tracker.MODEL_PRICING
        assert "local" in tracker.MODEL_PRICING
        
        for model, pricing in tracker.MODEL_PRICING.items():
            assert "input" in pricing
            assert "output" in pricing


class TestCostContext:
    """Test CostContext class."""
    
    def test_context_creation(self) -> None:
        """Test creating a cost context."""
        tracker = CostTracker()
        ctx = CostContext(tracker=tracker)
        
        assert ctx.tracker == tracker
        assert ctx.token_usage.total_tokens == 0
    
    def test_add_tokens(self) -> None:
        """Test adding tokens to context."""
        tracker = CostTracker()
        ctx = CostContext(tracker=tracker)
        
        ctx.add_tokens(prompt_tokens=100, completion_tokens=50)
        
        assert ctx.token_usage.prompt_tokens == 100
        assert ctx.token_usage.completion_tokens == 50
        assert ctx.token_usage.total_tokens == 150
    
    def test_get_summary(self) -> None:
        """Test getting cost summary."""
        tracker = CostTracker()
        ctx = CostContext(tracker=tracker)
        
        ctx.add_tokens(prompt_tokens=1000, completion_tokens=500)
        summary = ctx.get_summary()
        
        assert "tokens" in summary
        assert "cost" in summary
        assert "execution_time_ms" in summary
        assert "model" in summary
        assert summary["tokens"]["total"] == 1500
