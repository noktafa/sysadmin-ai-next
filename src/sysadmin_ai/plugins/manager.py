"""Plugin manager for loading and managing plugins."""

from __future__ import annotations

import importlib.metadata
import logging
from typing import Any

from sysadmin_ai.plugins.base import Plugin

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "sysadmin_ai.plugins"


class PluginManager:
    """Manages plugin discovery and execution."""

    def __init__(self) -> None:
        self._plugins: list[Plugin] = []
        self._load_plugins()

    def _load_plugins(self) -> None:
        """Load plugins from entry points."""
        try:
            entry_points = importlib.metadata.entry_points()
            
            # Handle different Python versions' entry_points API
            if hasattr(entry_points, "select"):
                # Python 3.10+
                plugins_eps = entry_points.select(group=ENTRY_POINT_GROUP)
            else:
                # Python 3.9
                plugins_eps = entry_points.get(ENTRY_POINT_GROUP, [])

            for ep in plugins_eps:
                try:
                    plugin_class = ep.load()
                    if issubclass(plugin_class, Plugin):
                        plugin = plugin_class()
                        self._plugins.append(plugin)
                        logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")
                    else:
                        logger.warning(f"Plugin {ep.name} does not inherit from Plugin base class")
                except Exception as e:
                    logger.error(f"Failed to load plugin {ep.name}: {e}")
        except Exception as e:
            logger.warning(f"Could not load plugins: {e}")

    def register_plugin(self, plugin: Plugin) -> None:
        """Manually register a plugin instance.

        Args:
            plugin: Plugin instance to register
        """
        self._plugins.append(plugin)
        logger.info(f"Manually registered plugin: {plugin.name}")

    def get_plugin_for_command(self, command: str) -> Plugin | None:
        """Find a plugin that can handle the given command.

        Args:
            command: The command to handle

        Returns:
            Plugin instance or None
        """
        for plugin in self._plugins:
            if plugin.can_handle(command):
                return plugin
        return None

    async def execute_with_plugin(
        self,
        command: str,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Execute a command using an appropriate plugin.

        Args:
            command: The command to execute
            context: Execution context

        Returns:
            Execution result or None if no plugin handles it
        """
        plugin = self.get_plugin_for_command(command)
        if plugin:
            return await plugin.execute(command, context)
        return None

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all loaded plugins.

        Returns:
            List of plugin information dictionaries
        """
        return [plugin.get_info() for plugin in self._plugins]

    def get_plugin(self, name: str) -> Plugin | None:
        """Get a plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None
        """
        for plugin in self._plugins:
            if plugin.name == name:
                return plugin
        return None
