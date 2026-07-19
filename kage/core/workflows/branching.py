"""core/workflows/branching.py — conditional branching + per-step retry (Phase 5).

An additive refinement layered on top of the existing SQLite workflow engine. A
step may declare a ``branch`` rule (``field`` equals/contains a value → then/else
step id) and a ``retry`` policy (max_attempts + base_delay + backoff_factor).
A step may also set ``next`` to an explicit successor (``None`` = terminal).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..health import run_with_retry
from ..result import ToolResult


@dataclass
class Branch:
    field: str = "status"            # status | data | meta.<key>
    equals: Any = None
    contains: Optional[str] = None
    then_step: Optional[str] = None
    else_step: Optional[str] = None


@dataclass
class Retry:
    max_attempts: int = 1
    base_delay: float = 0.05
    backoff_factor: float = 2.0


@dataclass
class Step:
    id: str
    name: str
    agent: str
    action: str
    input: Dict[str, Any] = field(default_factory=dict)
    branch: Optional[Branch] = None
    retry: Optional[Retry] = None
    next: Optional[str] = None       # resolved later: None sentinel = terminal


@dataclass
class Workflow:
    entry: str
    steps: List[Step]

    def step(self, step_id: str) -> Optional[Step]:
        return next((s for s in self.steps if s.id == step_id), None)


def _field_value(result: ToolResult, field: str) -> Any:
    if field == "status":
        return result.status
    if field == "data":
        return result.data
    if field.startswith("meta."):
        return result.meta.get(field.split(".", 1)[1])
    return None


def evaluate_branch(result: ToolResult, branch: Branch) -> Optional[str]:
    value = _field_value(result, branch.field)
    if branch.equals is not None:
        matched = value == branch.equals
    elif branch.contains is not None:
        matched = isinstance(value, str) and branch.contains in value
    else:
        matched = False
    return branch.then_step if matched else branch.else_step


def execute_workflow(wf: Workflow, runner: Callable[[Step, int], ToolResult],
                     *, max_steps: int = 100,
                     resume_from: Optional[str] = None) -> Dict[str, Any]:
    """Run a workflow with branching + retries; return results, path and ok flag.

    ``runner(step, attempt)`` performs one step attempt and returns a
    ``ToolResult``. Resume after a restart by passing ``resume_from``.
    """
    results: Dict[str, Dict[str, Any]] = {}
    visited: List[str] = []
    current = resume_from or wf.entry
    steps = 0
    while current and steps < max_steps:
        steps += 1
        step = wf.step(current)
        if step is None:
            break
        if step.retry:
            res = run_with_retry(lambda attempt, s=step: runner(s, attempt),
                                 max_attempts=step.retry.max_attempts,
                                 base_delay=step.retry.base_delay,
                                 backoff_factor=step.retry.backoff_factor)
        else:
            res = runner(step, 1)
        results[step.id] = res.to_dict()
        visited.append(step.id)
        if not res.ok:
            break
        nxt = evaluate_branch(res, step.branch) if step.branch else None
        if nxt is None:
            nxt = step.next  # explicit successor, or None (terminal)
        current = nxt
    return {
        "results": results,
        "visited": visited,
        "ok": bool(results) and all(r["status"] == "ok" for r in results.values()),
    }
