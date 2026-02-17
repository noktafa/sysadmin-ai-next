"""Base plugin classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class PluginMetadata:
    """Plugin metadata."""
    
    name: str
    version: str
    description: str
    author: str
    requires: list[str] = None
    
    def __post_init__(self) -> None:
        if self.requires is None:
            self.requires = []


class Plugin(ABC):
    """Base plugin class."""
    
    metadata: PluginMetadata
    
    def __init__(self) -> None:
        """Initialize plugin."""
        pass
    
    @abstractmethod
    def initialize(self, config: dict[str, Any]) -> None:
        """Initialize plugin with configuration."""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Clean up plugin resources."""
        pass


class ExecutorPlugin(Plugin):
    """Plugin for custom command executors."""
    
    @abstractmethod
    def execute(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Execute a command.
        
        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            timeout: Timeout in seconds
        
        Returns:
            Execution result with stdout, stderr, exit_code, etc.
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this executor is available in the current environment."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Executor name."""
        pass


class ToolPlugin(Plugin):
    """Plugin for custom tools/functions."""
    
    @abstractmethod
    def get_tools(self) -> list[dict[str, Any]]:
        """Get tool definitions for LLM.
        
        Returns:
            List of tool definitions in OpenAI function format
        """
        pass
    
    @abstractmethod
    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
        
        Returns:
            Tool execution result
        """
        pass
