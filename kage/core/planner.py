"""core/planner.py — turns a user request into an execution plan (KAGE v2).

The Planner is the conductor's first step: understand intent, decompose the task,
and select which on-demand agents are needed (in order). It never executes — it
produces a structured ``ExecutionPlan`` the orchestrator runs. A rule-based
planner works without an LLM; when an LLM is wired, it enriches the plan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .events import EventBus
from .result import ToolResult


@dataclass
class PlanStep:
    agent: str
    task: Dict[str, Any]
    rationale: str = ""
    depends_on: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"agent": self.agent, "task": self.task, "rationale": self.rationale,
                "depends_on": list(self.depends_on)}


@dataclass
class ExecutionPlan:
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    estimated_agents: int = 0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"goal": self.goal,
                "steps": [s.to_dict() for s in self.steps],
                "estimated_agents": self.estimated_agents or len({s.agent for s in self.steps}),
                "notes": self.notes}


# keyword -> (agent, rationale) routing table used by the rule-based planner.
_ROUTING = [
    (re.compile(r"\b(search|news|google|look up)\b", re.I), "research",
     "Information retrieval needs the research agent."),
    (re.compile(r"\b(code|refactor|implement|bug|function|class|test|repo)\b", re.I), "opencode-bridge",
     "Software work delegates to the OpenCode bridge."),
    (re.compile(r"\b(click|type|screen|gui|mouse|keyboard|window)\b", re.I), "openclaw-bridge",
     "GUI/computer control delegates to the OpenClaw bridge."),
    (re.compile(r"\b(remember|memory|recall|preference)\b", re.I), "memory",
     "Persistence is handled by the memory service."),
    (re.compile(r"\b(battery|storage|cpu|memory usage|disk|health|device)\b", re.I), "system",
     "Device telemetry comes from the system agent."),
    (re.compile(r"\b(note|vault|obsidian|write to)\b", re.I), "obsidian",
     "Note persistence targets the Obsidian vault."),
    (re.compile(r"\b(secure|vulnerab|audit|cve|safety)", re.I), "security",
     "Security analysis runs the security agent."),
]


class Planner:
    """Produces an ExecutionPlan for a goal."""

    def __init__(self, *, llm: Optional[Any] = None, bus: Optional[EventBus] = None) -> None:
        self.llm = llm
        self.bus = bus

    def plan(self, goal: str) -> ExecutionPlan:
        plan = self._rule_plan(goal)
        if self.llm is not None:
            try:
                enriched = self.llm(goal, plan.to_dict())
                if isinstance(enriched, dict):
                    plan.notes = str(enriched.get("notes", plan.notes))
            except Exception:  # noqa: BLE001
                pass
        if self.bus:
            self.bus.publish("plan.created", {"goal": goal,
                          "steps": len(plan.steps), "agents": plan.estimated_agents},
                          source="planner")
        return plan

    def _rule_plan(self, goal: str) -> ExecutionPlan:
        steps: List[PlanStep] = []
        used = set()
        for pattern, agent, rationale in _ROUTING:
            if pattern.search(goal) and agent not in used:
                steps.append(PlanStep(agent=agent, task={"goal": goal}, rationale=rationale))
                used.add(agent)
        # default: a conversational planner agent
        if not steps:
            steps.append(PlanStep(agent="planner", task={"goal": goal},
                                  rationale="No specialized route matched; reason about the request."))
        # improvement loop: after the work, let the harness evaluate it
        steps.append(PlanStep(agent="harness", task={"goal": goal, "evaluate": True},
                              rationale="Continuous improvement: benchmark this run.",
                              depends_on=[s.agent for s in steps]))
        return ExecutionPlan(goal=goal, steps=steps,
                             notes="rule-based plan" if not self.llm else "llm-enriched plan")
