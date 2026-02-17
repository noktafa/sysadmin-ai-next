"""Core SysAdmin AI functionality."""

from __future__ import annotations

import logging
from typing import Any

from sysadmin_ai.policy.engine import PolicyEngine
from sysadmin_ai.plugins.manager import PluginManager
from sysadmin_ai.sandbox.isolation import SessionIsolation
from sysadmin_ai.cost.tracker import CostTracker
from sysadmin_ai.recovery.fuzzy import FuzzyRecovery
from sysadmin_ai.playbooks.generator import PlaybookGenerator

logger = logging.getLogger(__name__)


class SysAdminAI:
    """Main SysAdmin AI orchestrator."""

    def __init__(
        self,
        user_id: str | None = None,
        enable_opa: bool = True,
        dry_run: bool = False,
        track_costs: bool = True,
    ):
        self.user_id = user_id or "anonymous"
        self.dry_run = dry_run
        self.track_costs = track_costs

        # Initialize components
        self.policy_engine = PolicyEngine(enabled=enable_opa)
        self.plugin_manager = PluginManager()
        self.sandbox = SessionIsolation(user_id=self.user_id)
        self.cost_tracker = CostTracker(enabled=track_costs)
        self.recovery = FuzzyRecovery()
        self.playbook_generator = PlaybookGenerator()

        logger.info(f"SysAdminAI initialized for user: {self.user_id}")

    async def execute_command(
        self,
        command: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a command with full policy checking and recovery.

        Args:
            command: The command to execute
            context: Additional context for policy evaluation

        Returns:
            Execution result with status, output, and metadata
        """
        result = {
            "command": command,
            "user_id": self.user_id,
            "dry_run": self.dry_run,
            "allowed": False,
            "executed": False,
            "output": None,
            "error": None,
            "suggestions": [],
            "cost": None,
        }

        # Check policy
        policy_result = await self.policy_engine.evaluate(command, context or {})
        if not policy_result.allowed:
            result["error"] = f"Policy violation: {policy_result.reason}"
            
            # Get recovery suggestions
            suggestions = await self.recovery.suggest_alternatives(
                command, 
                policy_result.violations
            )
            result["suggestions"] = suggestions
            return result

        result["allowed"] = True

        if self.dry_run:
            result["output"] = f"[DRY RUN] Would execute: {command}"
            return result

        # Execute in sandbox
        try:
            with self.cost_tracker.track() as cost_ctx:
                execution_result = await self.sandbox.execute(command)
                result["executed"] = True
                result["output"] = execution_result.output
                result["cost"] = cost_ctx.get_summary()
        except Exception as e:
            result["error"] = str(e)
            logger.exception("Command execution failed")

        return result

    def export_session(self, format_type: str = "ansible") -> str:
        """Export current session as a playbook.

        Args:
            format_type: Output format (ansible, terraform, shell)

        Returns:
            Generated playbook content
        """
        return self.playbook_generator.export(
            self.sandbox.get_history(),
            format_type=format_type,
        )
