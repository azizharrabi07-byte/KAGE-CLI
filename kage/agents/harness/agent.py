"""agents/harness/agent.py — the flagship continuous-improvement agent.

The Harness Agent does NOT solve user tasks. Its sole job is to improve OTHER
agents. For each run it evaluates prompts, measures token usage & latency,
detects weaknesses, and produces a candidate improvement + a benchmark report.
It never deploys changes — it only proposes and lets KAGE decide whether to
accept the upgrade.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ...core.base_agent import BaseAgent

# Weights for the composite "health" score (0-100).
_WEIGHTS = {"success": 40, "latency": 25, "stability": 20, "prompt": 15}


@dataclass
class BenchmarkResult:
    agent: str
    samples: int
    success_rate: float
    latency_ms: List[float] = field(default_factory=list)
    variance: float = 0.0
    health: float = 0.0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"agent": self.agent, "samples": self.samples,
                "success_rate": round(self.success_rate, 3),
                "latency_ms_avg": round(statistics.mean(self.latency_ms), 2) if self.latency_ms else 0.0,
                "latency_ms_p95": _percentile(self.latency_ms, 95),
                "variance": round(self.variance, 2),
                "health": round(self.health, 1), "notes": self.notes}


def _percentile(values: List[float], pct: int) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((pct / 100) * (len(s) - 1)))))
    return round(s[k], 2)


class HarnessAgent(BaseAgent):
    name = "harness"
    kind = "harness"
    description = "Evaluates, benchmarks and proposes improvements to other agents."
    emoji = "🔧"

    def wake(self) -> None:
        self._awake = True
        self._reports: List[Dict[str, Any]] = []

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        op = str(task.get("op", task.get("action", "evaluate")))
        if op == "evaluate":
            return self.evaluate(task)
        if op == "benchmark":
            return self.benchmark(task)
        if op == "compare":
            return self.compare(task)
        if op == "propose":
            return self.propose_improvement(task)
        return {"status": "error", "data": None, "error": f"unknown harness op: {op}"}

    # -- evaluate a finished run --------------------------------------------
    def evaluate(self, task: Dict[str, Any]) -> Dict[str, Any]:
        plan = task.get("plan") or {}
        results = task.get("results") or []
        steps = plan.get("steps", [])
        weak = []
        for r in results:
            if r.get("status") != "ok":
                weak.append({"agent": r.get("agent"), "issue": r.get("error") or "non-ok result"})
        score = 100 - 15 * len(weak)
        report = {"goal": task.get("goal"), "steps": len(steps),
                  "failures": weak, "score": max(0, score),
                  "recommendation": ("all steps ok" if not weak else "review failing agents")}
        self._reports.append(report)
        return {"status": "ok", "data": report, "error": None}

    # -- benchmark: run a callable N times and measure ----------------------
    def benchmark(self, task: Dict[str, Any]) -> Dict[str, Any]:
        agent_name = str(task.get("agent", "unknown"))
        runs = task.get("runs") or []
        fn = task.get("fn")  # optional Callable[[int], Any] (in-process only)
        latencies: List[float] = []
        successes = 0
        samples = 0
        # If raw run records are provided (status/durationMs), use them.
        for run in runs:
            samples += 1
            latencies.append(float(run.get("durationMs", run.get("latency_ms", 0))))
            if run.get("ok", run.get("status") == "ok"):
                successes += 1
        # Otherwise, if a callable was passed, invoke it n times.
        if fn is not None and callable(fn):
            n = int(task.get("iterations", 5))
            for i in range(n):
                t0 = time.perf_counter()
                try:
                    fn(i)
                    successes += 1
                except Exception:  # noqa: BLE001
                    pass
                latencies.append((time.perf_counter() - t0) * 1000)
                samples += 1
        success_rate = successes / samples if samples else 0.0
        variance = statistics.pvariance(latencies) if len(latencies) > 1 else 0.0
        health = self._health(success_rate, statistics.mean(latencies) if latencies else 1000, variance)
        result = BenchmarkResult(agent=agent_name, samples=samples, success_rate=success_rate,
                                 latency_ms=latencies, variance=variance, health=health)
        return {"status": "ok", "data": result.to_dict(), "error": None}

    @staticmethod
    def _health(success_rate: float, latency_avg: float, variance: float) -> float:
        # success contribution (0-40)
        s = _WEIGHTS["success"] * success_rate
        # latency contribution (0-25): <200ms full, degrades to 0 at 3000ms
        l = _WEIGHTS["latency"] * max(0.0, 1 - (latency_avg - 200) / 2800)
        # stability contribution (0-20): penalise high variance
        v = _WEIGHTS["stability"] * max(0.0, 1 - min(variance / 1_000_000, 1))
        # prompt baseline (0-15): placeholder until prompt analysis is wired
        p = _WEIGHTS["prompt"] * 0.8
        return s + l + v + p

    # -- compare two implementations ----------------------------------------
    def compare(self, task: Dict[str, Any]) -> Dict[str, Any]:
        baseline = task.get("baseline", {})
        candidate = task.get("candidate", {})
        b_health = float(baseline.get("health", 0))
        c_health = float(candidate.get("health", 0))
        delta = round(c_health - b_health, 1)
        return {"status": "ok", "data": {
            "baseline": baseline, "candidate": candidate, "delta": delta,
            "winner": "candidate" if delta > 0 else ("baseline" if delta < 0 else "tie"),
            "recommended": delta > 0, "note": "Harness never deploys; KAGE decides."}, "error": None}

    # -- propose an improvement (does NOT apply it) -------------------------
    def propose_improvement(self, task: Dict[str, Any]) -> Dict[str, Any]:
        agent_name = str(task.get("agent", "unknown"))
        weak = task.get("weaknesses", [])
        suggestions: List[str] = []
        if any("latency" in str(w).lower() for w in weak):
            suggestions.append("Cache repeated sub-results; reduce redundant calls.")
        if any("error" in str(w).lower() or "fail" in str(w).lower() for w in weak):
            suggestions.append("Add retry with backoff and a graceful fallback path.")
        if any("token" in str(w).lower() for w in weak):
            suggestions.append("Trim the system prompt; compress context before the LLM call.")
        if not suggestions:
            suggestions.append("No obvious weakness detected; keep the current prompt.")
        proposal = {"agent": agent_name, "weaknesses": weak, "suggestions": suggestions,
                    "applied": False, "requires_approval": True,
                    "note": "Benchmark a candidate before accepting this upgrade."}
        return {"status": "ok", "data": proposal, "error": None}

    def sleep(self) -> None:
        self._awake = False
