"""agents/obsidian/agent.py — Obsidian vault agent (Local REST API)."""

from __future__ import annotations
from typing import Any, Dict

from ...core.base_agent import BaseAgent
from ...core.integrations.obsidian import ObsidianIntegration


class ObsidianAgent(BaseAgent):
    name = "obsidian"
    kind = "obsidian"
    description = "Manages your Obsidian vault: list, read, write, search."
    emoji = "📓"

    def wake(self) -> None:
        self.integration = ObsidianIntegration(config=self.config, timeout=15.0)
        self._awake = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        op = str(task.get("op", task.get("action", "status")))
        if op in ("status", "obsidian.status"):
            return self.integration.health_check().to_dict()
        if op in ("list", "obsidian.list"):
            return {"status": "ok", "data": self._call(self.integration.list_files), "error": None}
        if op in ("read", "obsidian.read"):
            return {"status": "ok", "data": self._call(self.integration.read_file, task.get("path", "")), "error": None}
        if op in ("write", "create", "obsidian.write"):
            res = self.integration.send({"path": task.get("path", ""), "content": task.get("content", "")})
            return res.to_dict()
        if op in ("append", "obsidian.append"):
            res = self.integration.health_check()
            if not res.ok:
                return res.to_dict()
            return {"status": "ok", "data": self._call(self.integration.append_file, task.get("path", ""), task.get("content", "")), "error": None}
        if op in ("search", "obsidian.search"):
            return {"status": "ok", "data": self._call(self.integration.search, str(task.get("query", "")), limit=int(task.get("limit", 20))), "error": None}
        return {"status": "error", "data": None, "error": f"unknown obsidian op: {op}"}

    @staticmethod
    def _call(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}

    def sleep(self) -> None:
        if hasattr(self, "integration"):
            self.integration.disconnect()
        self._awake = False
