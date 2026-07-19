"""core/tools/crew.py — multi-agent orchestration tool.

Lets the supervisor fan a task out across several agents and merge their
structured results. This is the "crew" primitive for complex workflows.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base import Tool, ToolMeta, ToolSchema


class CrewTool(Tool):
    meta = ToolMeta(
        name="crew.run",
        description="Dispatch a task to multiple agents and merge results.",
        schema=ToolSchema(required=["task"], optional={"agents": "list"}),
    )

    def __init__(self, registry) -> None:
        super().__init__()
        self.registry = registry

    def run(self, args: Dict[str, Any], user_id: str = "cli") -> Dict[str, Any]:
        task = args["task"]
        names: List[str] = args.get("agents") or self.registry.list()
        merged: Dict[str, Any] = {}
        for name in names:
            try:
                agent = self.registry.get(name)
                if not agent:
                    continue
                if not agent.is_awake:
                    agent.wake()
                merged[name] = agent.execute({"task": task, "user_id": user_id})
            except Exception as exc:  # noqa: BLE001
                merged[name] = {"error": str(exc)}
        return {"ok": True, "task": task, "results": merged}
