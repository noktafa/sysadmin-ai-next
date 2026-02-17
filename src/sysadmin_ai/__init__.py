"""SysAdmin AI Next - Advanced AI-powered system administration assistant."""

__version__ = "0.1.0"
__all__ = ["SysAdminAI", "PolicyEngine", "PluginManager"]

from sysadmin_ai.policy.engine import PolicyEngine
from sysadmin_ai.plugins.manager import PluginManager
from sysadmin_ai.core import SysAdminAI
