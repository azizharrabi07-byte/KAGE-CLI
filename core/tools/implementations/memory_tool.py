#!/usr/bin/env python3
"""
memory_tool.py — User Memory Search & Storage Tool.
Part of Phase 8 Tool Framework.
"""

from typing import Dict, Any
from core.memory import MemoryManager, MemoryType
from core.tools.base import BaseTool, ToolMetadata, PermissionLevel
from core.tools.registry import ToolRegistry


class MemoryTool(BaseTool):
    """Executes vector search or fact storage in memory manager."""

    def __init__(self):
        super().__init__(ToolMetadata(
            name="user_memory",
            description="Searches user memories or stores new facts",
            category="memory",
            permission_level=PermissionLevel.SAFE,
            parameters_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "search | remember | recall"},
                    "user_id": {"type": "string", "description": "Target user ID"},
                    "query": {"type": "string", "description": "Query or fact text"}
                },
                "required": ["action"]
            }
        ))
        self.memory_mgr = MemoryManager()

    def run(self, args: Dict[str, Any]) -> Any:
        action = args["action"]
        user_id = args.get("user_id", "default")
        query = args.get("query", "")

        if action == "search":
            return self.memory_mgr.search_memories(query, user_id=user_id)
        elif action == "remember":
            item = self.memory_mgr.add_memory(query, user_id=user_id, memory_type=MemoryType.KNOWLEDGE, importance=8.0)
            return {"status": "saved", "item_id": item.item_id}
        elif action == "recall":
            return self.memory_mgr.recall_recent_context(user_id=user_id)
        else:
            raise ValueError(f"Unknown memory action: '{action}'")


ToolRegistry.register(MemoryTool())
