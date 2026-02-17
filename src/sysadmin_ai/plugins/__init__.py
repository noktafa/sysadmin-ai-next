"""Plugin system for extensible executors and tools."""

from .manager import PluginManager
from .base import Plugin, ExecutorPlugin, ToolPlugin

__all__ = ["PluginManager", "Plugin", "ExecutorPlugin", "ToolPlugin"]
