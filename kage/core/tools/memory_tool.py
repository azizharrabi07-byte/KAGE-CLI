"""core/tools/memory_tool.py — exposes long-term memory as a tool."""

from __future__ import annotations

from typing import Any, Dict

from .base import Tool, ToolMeta, ToolSchema


class MemoryTool(Tool):
    meta = ToolMeta(
        name="memory.recall",
        description="Recall a value from long-term memory by key.",
        schema=ToolSchema(required=["key"], optional={"user_id": "str"}),
    )

    def __init__(self, memory_store) -> None:
        super().__init__()
        self.memory = memory_store

    def run(self, args: Dict[str, Any], user_id: str = "cli") -> Dict[str, Any]:
        key = str(args["key"])
        uid = str(args.get("user_id", user_id))
        store = self.memory.get(uid)
        if key in store:
            return {"ok": True, "key": key, "value": store[key]}
        return {"ok": False, "key": key, "error": "not found"}
