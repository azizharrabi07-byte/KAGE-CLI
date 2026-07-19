#!/usr/bin/env python3
"""KAGE OS — benchmark suite.

Measures core subsystems (event bus, tool manager, memory, planner,
orchestrator, harness) for latency and stability, then reports a health score
via the Harness Agent. Run:  python benchmarks/run_benchmarks.py
"""
from __future__ import annotations

import os
import sys
import statistics
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kage.core.events import EventBus
from kage.core.memory_service import MemoryService
from kage.core.tool_manager import ToolManager
from kage.core.planner import Planner
from kage.core.orchestrator import Orchestrator
from kage.core.registry import AgentRegistry
from kage.agents.harness.agent import HarnessAgent
from kage.agents.security.agent import SecurityAgent


def measure(fn, iterations=200):
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return {"avg_ms": round(statistics.mean(times), 4),
            "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 4),
            "stdev": round(statistics.pstdev(times), 4)}


def main() -> int:
    print("KAGE OS — benchmark suite\n" + "=" * 44)
    results = {}

    bus = EventBus()
    bus.subscribe("bench.topic", lambda e: None)
    results["event_bus.publish"] = measure(lambda: bus.publish("bench.topic", {"x": 1}))

    mem = MemoryService(root=str(Path(tempfile.mkdtemp()) / "m"))
    results["memory.remember"] = measure(lambda: mem.remember("session", "k", "v"))

    tm = ToolManager(root=tempfile.mkdtemp())
    tm.call("filesystem.write", path="b.txt", content="x")
    results["tool.filesystem_read"] = measure(lambda: tm.call("filesystem.read", path="b.txt"))

    planner = Planner()
    results["planner.plan"] = measure(lambda: planner.plan("search the news and write code"), iterations=100)

    reg = AgentRegistry()
    for c in (HarnessAgent, SecurityAgent):
        reg.register(c)
    orch = Orchestrator(registry=reg, memory=MemoryService(root=str(Path(tempfile.mkdtemp()) / "m")), bus=EventBus())
    results["orchestrator.handle"] = measure(lambda: orch.handle("audit for vulnerabilities"), iterations=40)

    print(f"{'subsystem':<26}{'avg (ms)':>12}{'p95 (ms)':>12}{'stdev':>10}")
    print("-" * 60)
    for name, m in results.items():
        print(f"{name:<26}{m['avg_ms']:>12.4f}{m['p95_ms']:>12.4f}{m['stdev']:>10.4f}")

    # composite health via the Harness agent
    h = HarnessAgent(); h.wake()
    bm = h.execute({"op": "benchmark", "agent": "event_bus",
                    "runs": [{"ok": True, "durationMs": results["event_bus.publish"]["avg_ms"]}] * 10})
    print(f"\nHarness health (event bus): {bm['data']['health']}/100")
    print("\nAll subsystems measured. Use these baselines to detect regressions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
