"""Token usage and cost tracking per command."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token usage for a single operation."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: TokenUsage) -> None:
        """Add another TokenUsage to this one."""
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens


@dataclass
class CostRecord:
    """Cost record for a command execution."""

    command: str
    timestamp: str
    user_id: str
    token_usage: TokenUsage
    model: str
    estimated_cost_usd: float
    execution_time_ms: float


@dataclass
class CostContext:
    """Context for tracking costs during execution."""

    tracker: CostTracker
    start_time: float = field(default_factory=time.time)
    token_usage: TokenUsage = field(default_factory=TokenUsage)

    def add_tokens(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        """Add token usage."""
        self.token_usage.add(TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ))

    def get_summary(self) -> dict[str, Any]:
        """Get cost summary."""
        execution_time = (time.time() - self.start_time) * 1000
        cost = self.tracker._calculate_cost(self.token_usage, self.tracker.default_model)
        
        return {
            "tokens": {
                "prompt": self.token_usage.prompt_tokens,
                "completion": self.token_usage.completion_tokens,
                "total": self.token_usage.total_tokens,
            },
            "cost": f"{cost:.6f}",
            "execution_time_ms": f"{execution_time:.2f}",
            "model": self.tracker.default_model,
        }


class CostTracker:
    """Track token usage and costs per command."""

    # Pricing per 1K tokens (example pricing, update as needed)
    MODEL_PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "local": {"input": 0.0, "output": 0.0},
    }

    def __init__(
        self,
        enabled: bool = True,
        default_model: str = "gpt-3.5-turbo",
        log_file: str | Path | None = None,
    ):
        self.enabled = enabled
        self.default_model = default_model
        self._records: list[CostRecord] = []
        
        if log_file:
            self.log_file = Path(log_file)
        else:
            self.log_file = Path.home() / ".sysadmin-ai" / "costs.log"
        
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def track(
        self,
        command: str = "",
        user_id: str = "",
        model: str | None = None,
    ) -> Generator[CostContext, None, None]:
        """Context manager for tracking costs during command execution.

        Args:
            command: The command being executed
            user_id: User executing the command
            model: Model being used (defaults to default_model)

        Yields:
            CostContext for tracking tokens
        """
        ctx = CostContext(tracker=self)
        
        try:
            yield ctx
        finally:
            if self.enabled:
                self._record_cost(
                    command=command,
                    user_id=user_id,
                    token_usage=ctx.token_usage,
                    model=model or self.default_model,
                    execution_time_ms=(time.time() - ctx.start_time) * 1000,
                )

    def _record_cost(
        self,
        command: str,
        user_id: str,
        token_usage: TokenUsage,
        model: str,
        execution_time_ms: float,
    ) -> None:
        """Record cost information."""
        cost = self._calculate_cost(token_usage, model)
        
        record = CostRecord(
            command=command,
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            token_usage=token_usage,
            model=model,
            estimated_cost_usd=cost,
            execution_time_ms=execution_time_ms,
        )
        
        self._records.append(record)
        self._append_to_log(record)
        
        logger.debug(
            f"Cost tracked: {token_usage.total_tokens} tokens, "
            f"${cost:.6f} for command: {command[:50]}..."
        )

    def _calculate_cost(self, token_usage: TokenUsage, model: str) -> float:
        """Calculate cost based on token usage.

        Args:
            token_usage: Token usage data
            model: Model name

        Returns:
            Estimated cost in USD
        """
        pricing = self.MODEL_PRICING.get(model, self.MODEL_PRICING["gpt-3.5-turbo"])
        
        input_cost = (token_usage.prompt_tokens / 1000) * pricing["input"]
        output_cost = (token_usage.completion_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost

    def _append_to_log(self, record: CostRecord) -> None:
        """Append record to log file."""
        try:
            with open(self.log_file, "a") as f:
                f.write(
                    f"{record.timestamp}\t"
                    f"{record.user_id}\t"
                    f"{record.model}\t"
                    f"{record.token_usage.total_tokens}\t"
                    f"{record.estimated_cost_usd:.6f}\t"
                    f"{record.execution_time_ms:.2f}\t"
                    f"{record.command}\n"
                )
        except Exception as e:
            logger.error(f"Failed to write cost log: {e}")

    def get_user_stats(self, user_id: str) -> dict[str, Any]:
        """Get cost statistics for a user.

        Args:
            user_id: User to get stats for

        Returns:
            Statistics dictionary
        """
        user_records = [r for r in self._records if r.user_id == user_id]
        
        if not user_records:
            return {
                "user_id": user_id,
                "total_commands": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
            }

        total_tokens = sum(r.token_usage.total_tokens for r in user_records)
        total_cost = sum(r.estimated_cost_usd for r in user_records)
        
        return {
            "user_id": user_id,
            "total_commands": len(user_records),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "average_cost_per_command": round(total_cost / len(user_records), 6),
        }

    def get_global_stats(self) -> dict[str, Any]:
        """Get global cost statistics.

        Returns:
            Statistics dictionary
        """
        if not self._records:
            return {
                "total_commands": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "unique_users": 0,
            }

        total_tokens = sum(r.token_usage.total_tokens for r in self._records)
        total_cost = sum(r.estimated_cost_usd for r in self._records)
        unique_users = len(set(r.user_id for r in self._records))
        
        return {
            "total_commands": len(self._records),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "unique_users": unique_users,
            "average_cost_per_command": round(total_cost / len(self._records), 6),
        }

    def get_model_breakdown(self) -> dict[str, dict[str, Any]]:
        """Get cost breakdown by model.

        Returns:
            Dictionary mapping model names to statistics
        """
        breakdown: dict[str, dict[str, Any]] = {}
        
        for record in self._records:
            model = record.model
            if model not in breakdown:
                breakdown[model] = {
                    "commands": 0,
                    "tokens": 0,
                    "cost_usd": 0.0,
                }
            
            breakdown[model]["commands"] += 1
            breakdown[model]["tokens"] += record.token_usage.total_tokens
            breakdown[model]["cost_usd"] += record.estimated_cost_usd

        # Round costs for readability
        for model in breakdown:
            breakdown[model]["cost_usd"] = round(breakdown[model]["cost_usd"], 6)

        return breakdown
