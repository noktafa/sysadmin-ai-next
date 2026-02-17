"""Plugin manager for loading and managing plugins."""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import sys
from pathlib import Path
from typing import Any

from .base import ExecutorPlugin, Plugin, ToolPlugin


class PluginManager:
    """Manages plugin discovery, loading, and lifecycle."""
    
    ENTRY_POINT_GROUP = "sysadmin_ai.plugins"
    
    def __init__(self, plugin_dirs: list[str | Path] | None = None) -> None:
        """Initialize plugin manager.
        
        Args:
            plugin_dirs: Additional directories to search for plugins
        """
        self.plugin_dirs = [Path(d) for d in (plugin_dirs or [])]
        self._plugins: dict[str, Plugin] = {}
        self._executors: dict[str, ExecutorPlugin] = {}
        self._tools: dict[str, ToolPlugin] = {}
    
    def discover_plugins(self) -> list[str]:
        """Discover available plugins from entry points and directories.
        
        Returns:
            List of discovered plugin names
        """
        discovered = []
        
        # Discover from entry points
        try:
            entry_points = metadata.entry_points()
            if hasattr(entry_points, "select"):
                # Python 3.10+
                eps = entry_points.select(group=self.ENTRY_POINT_GROUP)
            else:
                # Python 3.9
                eps = entry_points.get(self.ENTRY_POINT_GROUP, [])
            
            for ep in eps:
                discovered.append(f"entry_point:{ep.name}")
        except Exception as e:
            print(f"Warning: Failed to discover entry points: {e}")
        
        # Discover from plugin directories
        for plugin_dir in self.plugin_dirs:
            if plugin_dir.exists():
                for plugin_file in plugin_dir.glob("*.py"):
                    if plugin_file.name != "__init__.py":
                        discovered.append(f"file:{plugin_file.stem}")
        
        return discovered
    
    def load_plugin(self, name: str, config: dict[str, Any] | None = None) -> Plugin | None:
        """Load a plugin by name.
        
        Args:
            name: Plugin name (with prefix: entry_point:name or file:name)
            config: Plugin configuration
        
        Returns:
            Loaded plugin instance or None if loading failed
        """
        if name in self._plugins:
            return self._plugins[name]
        
        config = config or {}
        
        try:
            if name.startswith("entry_point:"):
                plugin_name = name.replace("entry_point:", "")
                plugin = self._load_from_entry_point(plugin_name)
            elif name.startswith("file:"):
                plugin_name = name.replace("file:", "")
                plugin = self._load_from_file(plugin_name)
            else:
                # Try entry point first, then file
                plugin = self._load_from_entry_point(name)
                if plugin is None:
                    plugin = self._load_from_file(name)
            
            if plugin:
                plugin.initialize(config)
                self._plugins[name] = plugin
                
                # Register by type
                if isinstance(plugin, ExecutorPlugin):
                    self._executors[plugin.name] = plugin
                elif isinstance(plugin, ToolPlugin):
                    self._tools[name] = plugin
                
                return plugin
        
        except Exception as e:
            print(f"Error loading plugin {name}: {e}")
            return None
        
        return None
    
    def _load_from_entry_point(self, name: str) -> Plugin | None:
        """Load plugin from entry point."""
        try:
            entry_points = metadata.entry_points()
            if hasattr(entry_points, "select"):
                eps = entry_points.select(group=self.ENTRY_POINT_GROUP, name=name)
                ep = next(iter(eps), None)
            else:
                eps = entry_points.get(self.ENTRY_POINT_GROUP, [])
                ep = next((e for e in eps if e.name == name), None)
            
            if ep:
                plugin_class = ep.load()
                return plugin_class()
        except Exception as e:
            print(f"Error loading entry point {name}: {e}")
        
        return None
    
    def _load_from_file(self, name: str) -> Plugin | None:
        """Load plugin from file."""
        for plugin_dir in self.plugin_dirs:
            plugin_file = plugin_dir / f"{name}.py"
            if plugin_file.exists():
                # Add plugin dir to path temporarily
                if str(plugin_dir) not in sys.path:
                    sys.path.insert(0, str(plugin_dir))
                
                try:
                    spec = importlib.util.spec_from_file_location(name, plugin_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # Look for Plugin subclass
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (
                                isinstance(attr, type)
                                and issubclass(attr, Plugin)
                                and attr is not Plugin
                                and attr is not ExecutorPlugin
                                and attr is not ToolPlugin
                            ):
                                return attr()
                finally:
                    if str(plugin_dir) in sys.path:
                        sys.path.remove(str(plugin_dir))
        
        return None
    
    def get_executor(self, name: str) -> ExecutorPlugin | None:
        """Get an executor plugin by name."""
        return self._executors.get(name)
    
    def get_available_executors(self) -> dict[str, ExecutorPlugin]:
        """Get all available executors."""
        return {
            name: executor
            for name, executor in self._executors.items()
            if executor.is_available()
        }
    
    def get_tool_plugin(self, name: str) -> ToolPlugin | None:
        """Get a tool plugin by name."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> list[dict[str, Any]]:
        """Get all tools from all tool plugins."""
        tools = []
        for plugin in self._tools.values():
            tools.extend(plugin.get_tools())
        return tools
    
    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin."""
        if name in self._plugins:
            plugin = self._plugins[name]
            plugin.shutdown()
            del self._plugins[name]
            
            # Remove from type registries
            if isinstance(plugin, ExecutorPlugin):
                self._executors.pop(plugin.name, None)
            elif isinstance(plugin, ToolPlugin):
                self._tools.pop(name, None)
            
            return True
        return False
    
    def shutdown_all(self) -> None:
        """Shutdown all loaded plugins."""
        for plugin in self._plugins.values():
            try:
                plugin.shutdown()
            except Exception as e:
                print(f"Error shutting down plugin: {e}")
        
        self._plugins.clear()
        self._executors.clear()
        self._tools.clear()
