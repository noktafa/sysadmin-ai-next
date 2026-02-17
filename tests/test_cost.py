"""Tests for cost tracker."""

import pytest

from sysadmin_ai.cost.tracker import CostTracker, MODEL_PRICING, UsageRecord


class TestCostTracker:
    """Test cost tracker functionality."""
    
    @pytest.fixture
    def tracker(self, tmp_path) -> CostTracker:
        """Create a tracker with temporary directory."""
        return CostTracker(log_dir=tmp_path, model="gpt-3.5-turbo")
    
    def test_init(self, tracker: CostTracker) -> None:
        """Test tracker initialization."""
        assert tracker is not None
        assert tracker.model == "gpt-3.5-turbo"
    
    def test_start_session(self, tracker: CostTracker) -> None:
        """Test starting a session."""
        tracker.start_session("test-session")
        
        stats = tracker.get_session_stats()
        assert stats is not None
        assert stats.session_id == "test-session"
    
    def test_record_usage(self, tracker: CostTracker) -> None:
        """Test recording usage."""
        tracker.start_session("test-session")
        
        record = tracker.record_usage(
            command="ls -la",
            input_tokens=100,
            output_tokens=50,
            latency_ms=500,
        )
        
        assert record.command == "ls -la"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.latency_ms == 500
        assert record.cost_usd > 0
    
    def test_session_stats_accumulation(self, tracker: CostTracker) -> None:
        """Test that session stats accumulate correctly."""
        tracker.start_session("test-session")
        
        tracker.record_usage("cmd1", 100, 50, 100)
        tracker.record_usage("cmd2", 200, 100, 200)
        
        stats = tracker.get_session_stats()
        
        assert stats.total_commands == 2
        assert stats.total_input_tokens == 300
        assert stats.total_output_tokens == 150
        assert stats.total_latency_ms == 300
    
    def test_end_session(self, tracker: CostTracker) -> None:
        """Test ending a session."""
        tracker.start_session("test-session")
        tracker.record_usage("cmd", 100, 50, 100)
        
        stats = tracker.end_session()
        
        assert stats is not None
        assert stats.end_time is not None
        assert stats.duration_seconds >= 0
    
    def test_get_total_stats(self, tracker: CostTracker) -> None:
        """Test getting total stats."""
        tracker.start_session("session1")
        tracker.record_usage("cmd", 100, 50, 100)
        tracker.end_session()
        
        tracker.start_session("session2")
        tracker.record_usage("cmd", 200, 100, 200)
        tracker.end_session()
        
        stats = tracker.get_total_stats()
        
        assert stats["total_sessions"] == 2
        assert stats["total_commands"] == 2
        assert stats["total_input_tokens"] == 300
        assert stats["total_output_tokens"] == 150
        assert stats["total_cost_usd"] > 0
    
    def test_estimate_cost(self, tracker: CostTracker) -> None:
        """Test cost estimation."""
        estimate = tracker.estimate_cost(
            input_tokens=1000,
            output_tokens=500,
            model="gpt-3.5-turbo",
        )
        
        assert estimate["model"] == "gpt-3.5-turbo"
        assert estimate["input_tokens"] == 1000
        assert estimate["output_tokens"] == 500
        assert estimate["estimated_cost_usd"] > 0
        assert "pricing" in estimate
    
    def test_budget_check(self, tracker: CostTracker) -> None:
        """Test budget checking."""
        tracker.start_session("test")
        tracker.record_usage("cmd", 1000, 500, 100)
        
        # No budget set
        check = tracker.check_budget()
        assert check["budget_set"] is False
        
        # Set budget
        tracker.set_budget_alert(0.001)
        check = tracker.check_budget()
        
        assert check["budget_set"] is True
        assert check["budget_amount"] == 0.001
        assert "percent_used" in check


class TestUsageRecord:
    """Test UsageRecord dataclass."""
    
    def test_record_creation(self) -> None:
        """Test creating a usage record."""
        import time
        
        record = UsageRecord(
            timestamp=time.time(),
            session_id="test",
            command="ls -la",
            model="gpt-3.5-turbo",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            latency_ms=500,
        )
        
        assert record.session_id == "test"
        assert record.cost_usd == 0.001
        assert record.latency_ms == 500


class TestModelPricing:
    """Test model pricing constants."""
    
    def test_pricing_structure(self) -> None:
        """Test that pricing has correct structure."""
        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing
            assert "output" in pricing
            assert pricing["input"] >= 0
            assert pricing["output"] >= 0
    
    def test_gpt4_pricing(self) -> None:
        """Test GPT-4 pricing is higher than GPT-3.5."""
        assert MODEL_PRICING["gpt-4"]["input"] > MODEL_PRICING["gpt-3.5-turbo"]["input"]
        assert MODEL_PRICING["gpt-4"]["output"] > MODEL_PRICING["gpt-3.5-turbo"]["output"]
