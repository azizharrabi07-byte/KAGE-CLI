"""
KAGE OS Tools Framework Package.
Provides base tool interface, metadata structures, permission levels, and central tool registry.
"""

from .base import BaseTool, ToolMetadata, PermissionLevel, ToolResult
from .registry import ToolRegistry

__all__ = [
    "BaseTool",
    "ToolMetadata",
    "PermissionLevel",
    "ToolResult",
    "ToolRegistry",
]
