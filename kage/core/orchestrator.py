"""core/orchestrator.py — the KAGE conductor (v2 kernel).

The orchestrator is the only always-on component. On each task it:
    receive → plan → select agents → start on demand → execute → merge →
    store memory → terminate agent → return.

Agents are launched lazily, run their unit of work, return a structured
``ToolResult``, and are then terminated (``sleep``), minimizing RAM/CPU on
constrained devices like phones. All cross-cutting communication flows through
the event bus, never direct agent-to-agent calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .events import EventBus
from .memory_service import MemoryService
from .planner import ExecutionPlan, Planner
from .result import ToolResult
from .tool_manager import ToolManager

log = logging.getLogger("kage.orchestrator")


@dataclass
class RunRecord:
    goal: str
    plan: Dict[str, Any]
    results: List[Dict[str, Any]] = field(default_factory=list)
    ok: bool = True
    elapsed_ms: float = 0.0
    agent_calls: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"goal": self.goal, "plan": self.plan, "results": self.results,
                "ok": self.ok, "elapsed_ms": round(self.elapsed_ms, 1),
                "agent_calls": self.agent_calls}


class Orchestrator:
    """Coordinates agents on demand around a planner + shared services."""

    def __init__(self, *, registry: Any, planner: Optional[Planner] = None,
                 tools: Optional[ToolManager] = None,
                 memory: Optional[MemoryService] = None,
                 bus: Optional[EventBus] = None) -> None:
        self.registry = registry
        self.planner = planner or Planner()
        self.tools = tools
        self.memory = memory
        self.bus = bus or EventBus()
        self.runs: List[RunRecord] = []

    def handle(self, goal: str, user_id: str = "cli") -> RunRecord:
        start = time.perf_counter()
        self.bus.publish("task.received", {"goal": goal, "user_id": user_id}, source="orchestrator")
        plan = self.planner.plan(goal)
        self.bus.publish("task.planned", {"goal": goal, "steps": len(plan.steps)}, source="orchestrator")
        record = RunRecord(goal=goal, plan=plan.to_dict())
        outcomes: Dict[str, ToolResult] = {}

        for step in plan.steps:
            # honour simple dependencies: skip if any dependency failed
            if any(not outcomes.get(d, ToolResult.success()).ok for d in step.depends_on):
                self.bus.publish("step.skipped", {"agent": step.agent,
                                "reason": "dependency failed"}, source="orchestrator")
                continue
            res = self._run_agent(step.agent, {**step.task, "goal": goal,
                                               "plan": plan.to_dict(), "user_id": user_id})
            outcomes[step.agent] = res
            record.results.append({"agent": step.agent, **res.to_dict()})
            record.agent_calls += 1
            self.bus.publish("agent.completed", {"agent": step.agent,
                            "ok": res.ok, "durationMs": round(res.durationMs, 1)}, source="orchestrator")
            if self.memory:
                self.memory.remember("session", f"last:{step.agent}", res.status)
            # terminate the agent after its unit of work (on-demand lifecycle)
            self._terminate(step.agent)

        record.ok = all(r.get("status") == "ok" for r in record.results) or not record.results
        record.elapsed_ms = (time.perf_counter() - start) * 1000
        self.runs.append(record)
        if self.memory:
            self.memory.remember("session", "last_goal", goal)
            self.memory.remember("user", "last_seen", str(int(time.time())))
        self.bus.publish("task.completed", {"ok": record.ok,
                        "elapsed_ms": round(record.elapsed_ms, 1)}, source="orchestrator")
        return record

    def _run_agent(self, name: str, task: Dict[str, Any]) -> ToolResult:
        t0 = time.perf_counter()
        try:
            agent = self.registry.get(name, supervisor=self)
            if agent is None:
                return ToolResult.failure(f"agent not found: {name}", durationMs=(time.perf_counter() - t0) * 1000)
            if not agent.is_awake:
                agent.wake()
            raw = agent.execute(task)
            if isinstance(raw, dict):
                is_ok = raw.get("status", "ok") != "error" and bool(raw.get("ok", True))
                return ToolResult(
                    status="ok" if is_ok else "error",
                    data=raw.get("data"),
                    error=raw.get("error"),
                    durationMs=(time.perf_counter() - t0) * 1000,
                )
            return ToolResult(status="ok", data=raw, durationMs=(time.perf_counter() - t0) * 1000)
        except Exception as exc:  # noqa: BLE001
            return ToolResult.failure(str(exc), durationMs=(time.perf_counter() - t0) * 1000)

    def _terminate(self, name: str) -> None:
        try:
            agent = self.registry._instances.get(name)
            if agent and agent.is_awake:
                agent.sleep()
        except Exception:  # noqa: BLE001
            pass
