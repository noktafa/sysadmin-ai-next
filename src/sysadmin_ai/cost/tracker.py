"""Token usage and cost tracking."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


# Pricing per 1K tokens (as of 2024 - update as needed)
MODEL_PRICING = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
}


@dataclass
class UsageRecord:
    """A single usage record."""
    
    timestamp: float
    session_id: str
    command: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionStats:
    """Statistics for a session."""
    
    session_id: str
    total_commands: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    
    @property
    def average_latency_ms(self) -> float:
        """Average latency per command."""
        if self.total_commands == 0:
            return 0.0
        return self.total_latency_ms / self.total_commands
    
    @property
    def duration_seconds(self) -> float:
        """Session duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time


class CostTracker:
    """Track token usage and costs across sessions."""
    
    def __init__(
        self,
        log_dir: str | Path | None = None,
        model: str = "gpt-3.5-turbo",
    ) -> None:
        """Initialize cost tracker.
        
        Args:
            log_dir: Directory for usage logs
            model: Default model for pricing
        """
        self.log_dir = Path(log_dir) if log_dir else Path.home() / ".sysadmin-ai" / "costs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.model = model
        self._records: list[UsageRecord] = []
        self._session_stats: dict[str, SessionStats] = {}
        self._current_session: str | None = None
    
    def start_session(self, session_id: str) -> None:
        """Start tracking a new session."""
        self._current_session = session_id
        self._session_stats[session_id] = SessionStats(session_id=session_id)
    
    def end_session(self, session_id: str | None = None) -> SessionStats:
        """End a session and return stats."""
        sid = session_id or self._current_session
        if not sid:
            raise ValueError("No session to end")
        
        stats = self._session_stats.get(sid)
        if stats:
            stats.end_time = time.time()
        
        return stats
    
    def record_usage(
        self,
        command: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        model: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UsageRecord:
        """Record token usage for a command.
        
        Args:
            command: The command that was executed
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency_ms: API call latency in milliseconds
            model: Model used (defaults to self.model)
            session_id: Session ID (defaults to current session)
            metadata: Additional metadata
        
        Returns:
            The created usage record
        """
        model = model or self.model
        session_id = session_id or self._current_session or "unknown"
        
        # Calculate cost
        cost = self._calculate_cost(input_tokens, output_tokens, model)
        
        record = UsageRecord(
            timestamp=time.time(),
            session_id=session_id,
            command=command[:100],  # Truncate long commands
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            metadata=metadata or {},
        )
        
        self._records.append(record)
        
        # Update session stats
        if session_id in self._session_stats:
            stats = self._session_stats[session_id]
            stats.total_commands += 1
            stats.total_input_tokens += input_tokens
            stats.total_output_tokens += output_tokens
            stats.total_cost_usd += cost
            stats.total_latency_ms += latency_ms
        
        # Persist to log
        self._persist_record(record)
        
        return record
    
    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
    ) -> float:
        """Calculate cost in USD."""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-3.5-turbo"])
        
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        return round(input_cost + output_cost, 6)
    
    def _persist_record(self, record: UsageRecord) -> None:
        """Persist a record to the log file."""
        date_str = time.strftime("%Y-%m-%d")
        log_file = self.log_dir / f"usage_{date_str}.jsonl"
        
        with open(log_file, "a") as f:
            f.write(json.dumps(asdict(record)) + "\n")
    
    def get_session_stats(self, session_id: str | None = None) -> SessionStats | None:
        """Get stats for a session."""
        sid = session_id or self._current_session
        return self._session_stats.get(sid)
    
    def get_total_stats(self) -> dict[str, Any]:
        """Get total statistics across all sessions."""
        total_commands = sum(s.total_commands for s in self._session_stats.values())
        total_input = sum(s.total_input_tokens for s in self._session_stats.values())
        total_output = sum(s.total_output_tokens for s in self._session_stats.values())
        total_cost = sum(s.total_cost_usd for s in self._session_stats.values())
        total_latency = sum(s.total_latency_ms for s in self._session_stats.values())
        
        return {
            "total_sessions": len(self._session_stats),
            "total_commands": total_commands,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": round(total_cost, 4),
            "average_latency_ms": round(total_latency / total_commands, 2) if total_commands > 0 else 0,
        }
    
    def get_daily_report(self, date: str | None = None) -> dict[str, Any]:
        """Get a daily usage report.
        
        Args:
            date: Date string (YYYY-MM-DD) or None for today
        
        Returns:
            Daily usage report
        """
        date = date or time.strftime("%Y-%m-%d")
        log_file = self.log_dir / f"usage_{date}.jsonl"
        
        if not log_file.exists():
            return {"date": date, "records": [], "total_cost": 0.0}
        
        records = []
        total_cost = 0.0
        
        with open(log_file) as f:
            for line in f:
                try:
                    record = json.loads(line)
                    records.append(record)
                    total_cost += record.get("cost_usd", 0)
                except json.JSONDecodeError:
                    continue
        
        # Group by session
        sessions: dict[str, dict[str, Any]] = {}
        for record in records:
            sid = record["session_id"]
            if sid not in sessions:
                sessions[sid] = {
                    "commands": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                }
            sessions[sid]["commands"] += 1
            sessions[sid]["input_tokens"] += record["input_tokens"]
            sessions[sid]["output_tokens"] += record["output_tokens"]
            sessions[sid]["cost"] += record["cost_usd"]
        
        return {
            "date": date,
            "total_records": len(records),
            "total_cost_usd": round(total_cost, 4),
            "sessions": sessions,
        }
    
    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Estimate cost for a hypothetical usage.
        
        Args:
            input_tokens: Expected input tokens
            output_tokens: Expected output tokens
            model: Model to use for pricing
        
        Returns:
            Cost estimate
        """
        model = model or self.model
        cost = self._calculate_cost(input_tokens, output_tokens, model)
        
        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": cost,
            "pricing": MODEL_PRICING.get(model, MODEL_PRICING["gpt-3.5-turbo"]),
        }
    
    def set_budget_alert(self, budget_usd: float, callback: Callable[[float], None] | None = None) -> None:
        """Set a budget alert threshold.
        
        Args:
            budget_usd: Budget in USD
            callback: Function to call when budget is exceeded
        """
        self._budget_limit = budget_usd
        self._budget_callback = callback
    
    def check_budget(self) -> dict[str, Any]:
        """Check current spending against budget."""
        stats = self.get_total_stats()
        total_cost = stats["total_cost_usd"]
        
        budget = getattr(self, "_budget_limit", None)
        
        result = {
            "total_spent": total_cost,
            "budget_set": budget is not None,
            "budget_amount": budget,
            "over_budget": False,
            "percent_used": None,
        }
        
        if budget:
            result["over_budget"] = total_cost > budget
            result["percent_used"] = round((total_cost / budget) * 100, 2)
            
            if result["over_budget"] and hasattr(self, "_budget_callback"):
                self._budget_callback(total_cost)
        
        return result
    
    def export_report(self, output_path: str | Path, format: str = "json") -> Path:
        """Export a comprehensive usage report.
        
        Args:
            output_path: Path for output file
            format: Output format (json, csv, markdown)
        
        Returns:
            Path to exported file
        """
        output_path = Path(output_path)
        stats = self.get_total_stats()
        
        if format == "json":
            report = {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "summary": stats,
                "sessions": {
                    sid: {
                        "commands": s.total_commands,
                        "input_tokens": s.total_input_tokens,
                        "output_tokens": s.total_output_tokens,
                        "cost_usd": s.total_cost_usd,
                        "duration_seconds": s.duration_seconds,
                    }
                    for sid, s in self._session_stats.items()
                },
                "pricing": MODEL_PRICING,
            }
            output_path.write_text(json.dumps(report, indent=2))
        
        elif format == "csv":
            lines = ["timestamp,session_id,command,model,input_tokens,output_tokens,cost_usd,latency_ms"]
            for record in self._records:
                lines.append(
                    f"{record.timestamp},{record.session_id},{record.command},"
                    f"{record.model},{record.input_tokens},{record.output_tokens},"
                    f"{record.cost_usd},{record.latency_ms}"
                )
            output_path.write_text("\n".join(lines))
        
        elif format == "markdown":
            lines = [
                "# SysAdmin AI Cost Report",
                f"\nGenerated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                "\n## Summary",
                f"- Total Sessions: {stats['total_sessions']}",
                f"- Total Commands: {stats['total_commands']}",
                f"- Total Tokens: {stats['total_tokens']:,}",
                f"- Total Cost: ${stats['total_cost_usd']:.4f}",
                f"- Average Latency: {stats['average_latency_ms']}ms",
                "\n## Sessions",
                "| Session | Commands | Tokens | Cost | Duration |",
                "|---------|----------|--------|------|----------|",
            ]
            
            for sid, s in self._session_stats.items():
                tokens = s.total_input_tokens + s.total_output_tokens
                lines.append(
                    f"| {sid[:8]}... | {s.total_commands} | {tokens:,} | "
                    f"${s.total_cost_usd:.4f} | {s.duration_seconds:.0f}s |"
                )
            
            output_path.write_text("\n".join(lines))
        
        return output_path
