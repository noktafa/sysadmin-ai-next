"""SysAdmin AI Next - Advanced AI-powered system administration assistant."""

__version__ = "0.1.0"

# Core components - lazy imports to avoid circular dependencies
def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name == "PolicyEngine":
        from sysadmin_ai.policy.engine import PolicyEngine
        return PolicyEngine
    elif name == "PluginManager":
        from sysadmin_ai.plugins.manager import PluginManager
        return PluginManager
    elif name == "SandboxManager":
        from sysadmin_ai.sandbox.manager import SandboxManager
        return SandboxManager
    elif name == "PlaybookGenerator":
        from sysadmin_ai.playbooks.generator import PlaybookGenerator
        return PlaybookGenerator
    elif name == "CostTracker":
        from sysadmin_ai.cost.tracker import CostTracker
        return CostTracker
    elif name == "RecoveryEngine":
        from sysadmin_ai.recovery.recovery import RecoveryEngine
        return RecoveryEngine
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "PolicyEngine",
    "PluginManager",
    "SandboxManager",
    "PlaybookGenerator",
    "CostTracker",
    "RecoveryEngine",
]
