#!/usr/bin/env python3
"""
registry.py — Central Tool Registry for KAGE OS.
Manages tool discovery, metadata querying, schema validation, and permission checks.
Part of Phase 8 Tool Framework.
"""

import logging
from typing import Dict, List, Optional, Type, Any
from .base import BaseTool, ToolResult, PermissionLevel

logger = logging.getLogger("kage.tool_registry")


class ToolRegistry:
    """Central registry mapping tool names to BaseTool instances."""

    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool):
        """Register a BaseTool instance."""
        name = tool.metadata.name.lower()
        cls._tools[name] = tool
        logger.info(f"Registered tool: '{name}' [{tool.metadata.permission_level.value.upper()}]")

    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        """Retrieve tool by name."""
        return cls._tools.get(name.lower())

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        """List metadata for all registered tools."""
        return [
            {
                "name": t.metadata.name,
                "description": t.metadata.description,
                "category": t.metadata.category,
                "version": t.metadata.version,
                "permission": t.metadata.permission_level.value,
                "schema": t.metadata.parameters_schema,
            }
            for t in cls._tools.values()
        ]

    @classmethod
    def execute_tool(cls, name: str, args: Dict[str, Any], context: Optional[Any] = None) -> ToolResult:
        """Look up tool, verify permissions, and execute safely."""
        tool = cls.get_tool(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found in ToolRegistry")

        # Permission verification
        if tool.metadata.permission_level != PermissionLevel.SAFE and context and hasattr(context, "permissions"):
            approved = context.permissions.require_approval(
                f"tool.{name}",
                f"Execute tool '{name}' with arguments: {args}"
            )
            if not approved:
                return ToolResult(success=False, error=f"Execution of tool '{name}' denied by user")

        return tool.execute(args)
