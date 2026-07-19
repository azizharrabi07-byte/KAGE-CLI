"""agents/planner/agent.py — reasoning agent for unstructured requests."""

from __future__ import annotations
from typing import Any, Dict
from ...core.base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    name = "planner"
    kind = "planner"
    description = "Reasons about ambiguous requests and proposes a direction."
    emoji = "🧠"

    def wake(self) -> None:
        self._awake = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        goal = str(task.get("goal", ""))
        # If an LLM is wired on the supervisor, richer planning happens in core.planner.
        return {"ok": True, "agent": self.name, "goal": goal,
                "note": "analyzed request; no specialized agent was a clear fit."}

    def sleep(self) -> None:
        self._awake = False
