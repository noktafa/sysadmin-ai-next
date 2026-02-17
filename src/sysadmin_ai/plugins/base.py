"""Plugin system for custom executors."""

from __future__ import annotations

import importlib.metadata
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class Plugin(ABC):
    """Base class for SysAdmin AI plugins."""

    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    @abstractmethod
    async def execute(self, command: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute a command.

        Args:
            command: The command to execute
            context: Execution context

        Returns:
            Execution result
        """
        pass

    @abstractmethod
    def can_handle(self, command: str) -> bool:
        """Check if this plugin can handle the given command.

        Args:
            command: The command to check

        Returns:
            True if this plugin can handle the command
        """
        pass

    def get_info(self) -> dict[str, Any]:
        """Get plugin information."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }
