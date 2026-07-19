"""Tests for the KAGE v2 architecture: events, tool manager, memory service,
plugins, planner, orchestrator, harness agent.

Run:  python kage/tests/test_v2_architecture.py
"""

from __future__ import annotations
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from kage.core.events import EventBus, Event
from kage.core.memory_service import MemoryService, LAYERS
from kage.core.tool_manager import ToolManager
from kage.core.plugins import PluginManager, load_manifest, _parse_yaml
from kage.core.planner import Planner
from kage.core.orchestrator import Orchestrator
from kage.core.registry import AgentRegistry
from kage.agents.harness.agent import HarnessAgent
from kage.agents.planner.agent import PlannerAgent
from kage.agents.security.agent import SecurityAgent
from kage.agents.bridge import OpenCodeBridgeAgent, OpenClawBridgeAgent, BridgeAgent
from kage.core.base_agent import BaseAgent

_passed = 0; _failed = 0
def check(name, cond):
    global _passed, _failed
    if cond: _passed += 1
    else: _failed += 1; print(f"  FAIL: {name}")

# --- Event bus --------------------------------------------------------------
def test_event_bus_pubsub():
    bus = EventBus(); got = []
    bus.subscribe("task.received", lambda e: got.append(e.payload["x"]))
    bus.publish("task.received", {"x": 42}, source="t")
    check("bus exact deliver", got == [42])

def test_event_bus_wildcard():
    bus = EventBus(); topics = []
    bus.subscribe("agent.*", lambda e: topics.append(e.topic))
    bus.publish("agent.started", {}); bus.publish("agent.completed", {})
    bus.publish("task.received", {})
    check("bus wildcard matches prefix", topics == ["agent.started", "agent.completed"])

def test_event_bus_history():
    bus = EventBus()
    bus.publish("a.b", {}); bus.publish("a.b", {})
    check("bus history", len(bus.history("a.b")) == 2)

def test_event_bus_unsubscribe():
    bus = EventBus(); calls = []
    h = lambda e: calls.append(1)
    bus.subscribe("x", h); bus.publish("x", {})
    bus.unsubscribe("x", h); bus.publish("x", {})
    check("bus unsubscribe", len(calls) == 1)

def test_event_handler_isolated():
    bus = EventBus(); ok = []
    bus.subscribe("t", lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
    bus.subscribe("t", lambda e: ok.append(1))
    bus.publish("t", {})
    check("bus bad handler doesn't block others", ok == [1])

# --- Memory service ---------------------------------------------------------
def test_memory_layers():
    m = MemoryService(root=str(Path(tempfile.mkdtemp()) / "m"))
    m.remember("user", "name", "Kage")
    m.remember("session", "task", "x")
    check("memory recall user", m.recall("user", "name") == "Kage")
    check("memory recall session", m.recall("session", "task") == "x")
    check("memory isolated layers", m.recall("user", "task") is None)

def test_memory_search_and_clear():
    m = MemoryService(root=str(Path(tempfile.mkdtemp()) / "m"))
    m.remember("knowledge", "python", "great language")
    m.remember("user", "name", "Kage")
    hits = m.search("kage")
    check("memory search finds user", "user" in hits)
    m.clear_session()
    check("memory clear session", m.recall("session", "anything") is None)

def test_memory_invalid_layer():
    m = MemoryService(root=str(Path(tempfile.mkdtemp()) / "m"))
    try: m.remember("bogus", "k", "v"); check("memory bad layer rejected", False)
    except ValueError: check("memory bad layer rejected", True)

def test_memory_snapshot():
    m = MemoryService(root=str(Path(tempfile.mkdtemp()) / "m"))
    m.remember("longterm", "fact", "sky is blue")
    snap = m.snapshot()
    check("memory snapshot all layers", set(snap) == set(LAYERS))
    check("memory snapshot content", snap["longterm"]["fact"] == "sky is blue")

# --- Tool manager -----------------------------------------------------------
def test_tool_manager_builtin():
    tm = ToolManager(root=tempfile.mkdtemp())
    check("tool manager lists", "filesystem.read" in tm.list())
    check("tool manager count >=8", len(tm.list()) >= 8)

def test_tool_manager_fs():
    tm = ToolManager(root=tempfile.mkdtemp())
    check("tool write", tm.call("filesystem.write", path="f.txt", content="hi").ok)
    r = tm.call("filesystem.read", path="f.txt")
    check("tool read", r.ok and "hi" in r.data["content"])
    r = tm.call("filesystem.list")
    check("tool list", r.ok and "f.txt" in r.data["entries"])

def test_tool_manager_terminal_gated():
    tm = ToolManager(root=tempfile.mkdtemp())
    check("tool term echo", tm.call("terminal.run", command="echo hi").ok)
    check("tool term blocked", tm.call("terminal.run", command="rm -rf /").ok is False)
    check("tool unknown", tm.call("nope").ok is False)

def test_tool_manager_register_custom():
    tm = ToolManager(root=tempfile.mkdtemp())
    from kage.core.result import ToolResult
    tm.register("custom.add", lambda a, b: ToolResult.success({"sum": a + b}), "add")
    r = tm.call("custom.add", a=2, b=3)
    check("tool custom", r.ok and r.data["sum"] == 5)

# --- Plugins ----------------------------------------------------------------
def test_yaml_parser():
    d = _parse_yaml("name: x\nversion: 1.2.3\ntools:\n  - a\n  - b\n")
    check("yaml parse scalar", d["name"] == "x" and d["version"] == "1.2.3")
    check("yaml parse list", d["tools"] == ["a", "b"])

def test_plugin_discover_and_install():
    reg = AgentRegistry()
    pm = PluginManager(registry=reg, plugin_root="kage/plugins")
    found = pm.discover()
    check("plugin discover", len(found) >= 1 and found[0].name == "summarizer")
    n = pm.install_all()
    check("plugin install count", n == 1)
    check("plugin registered agent", "summarizer" in reg.list())
    a = reg.get("summarizer"); a.wake()
    r = a.execute({"text": "one. two. three. " * 10, "max_bullets": 2})
    check("plugin agent executes", r["status"] == "ok" and r["data"]["count"] <= 2)

def test_plugin_remove():
    reg = AgentRegistry()
    pm = PluginManager(registry=reg, plugin_root="kage/plugins")
    pm.install_all()
    check("plugin remove", pm.remove("summarizer") is True)
    check("plugin remove missing", pm.remove("nope") is False)
    check("plugin gone after remove", "summarizer" not in pm.installed)

# --- Planner ----------------------------------------------------------------
def test_planner_routing():
    p = Planner()
    agents = lambda g: [s.agent for s in p.plan(g).steps]
    check("plan search->research", "research" in agents("search the news"))
    check("plan code->opencode", "opencode-bridge" in agents("write some code"))
    check("plan gui->openclaw", "openclaw-bridge" in agents("click the button"))
    check("plan audit->security", "security" in agents("audit for vulnerabilities"))
    check("plan always ends harness", agents("anything")[-1] == "harness")

def test_planner_publishes_event():
    bus = EventBus(); seen = []
    bus.subscribe("plan.created", lambda e: seen.append(e.topic))
    Planner(bus=bus).plan("test")
    check("planner publishes plan.created", seen == ["plan.created"])

# --- Orchestrator -----------------------------------------------------------
def test_orchestrator_end_to_end():
    reg = AgentRegistry()
    for c in [HarnessAgent, SecurityAgent]: reg.register(c)
    bus = EventBus(); events = []
    bus.subscribe("task.*", lambda e: events.append(e.topic))
    o = Orchestrator(registry=reg, memory=MemoryService(root=str(Path(tempfile.mkdtemp())/"m")), bus=bus)
    rec = o.handle("audit for vulnerabilities")
    check("orch ran", bool(rec.results))
    check("orch has events", "task.received" in events and "task.completed" in events)
    check("orch stores session memory", o.memory.recall("session", "last_goal") == "audit for vulnerabilities")

def test_orchestrator_terminates_agents():
    class CountingAgent(BaseAgent):
        name = kind = "counter"
        wakes = 0; sleeps = 0
        def wake(self): self._awake = True; CountingAgent.wakes += 1
        def execute(self, task): return {"status": "ok", "data": {"n": 1}}
        def sleep(self): self._awake = False; CountingAgent.sleeps += 1
    reg = AgentRegistry(); reg.register(CountingAgent)
    o = Orchestrator(registry=reg, planner=Planner(), memory=MemoryService(root=str(Path(tempfile.mkdtemp())/"m")))
    # force the plan to route to counter
    from kage.core.planner import PlanStep, ExecutionPlan
    def fake_plan(goal):
        return ExecutionPlan(goal=goal, steps=[PlanStep(agent="counter", task={})])
    o.planner = type("P", (), {"plan": fake_plan})
    o.handle("go")
    check("orch starts agent on demand", CountingAgent.wakes == 1)
    check("orch terminates after work", CountingAgent.sleeps == 1)

# --- Harness agent ----------------------------------------------------------
def test_harness_evaluate():
    h = HarnessAgent(); h.wake()
    r = h.execute({"op": "evaluate", "goal": "x", "plan": {"steps": [1, 2]},
                   "results": [{"agent": "a", "status": "ok"}]})
    check("harness evaluate ok", r["status"] == "ok" and r["data"]["score"] == 100)

def test_harness_benchmark():
    h = HarnessAgent(); h.wake()
    r = h.execute({"op": "benchmark", "agent": "t", "fn": lambda i: i, "iterations": 4})
    check("harness benchmark samples", r["data"]["samples"] == 4 and r["data"]["success_rate"] == 1.0)
    check("harness health present", 0 <= r["data"]["health"] <= 100)

def test_harness_compare():
    h = HarnessAgent(); h.wake()
    r = h.execute({"op": "compare", "baseline": {"health": 60}, "candidate": {"health": 80}})
    check("harness compare winner", r["data"]["winner"] == "candidate" and r["data"]["recommended"])

def test_harness_propose():
    h = HarnessAgent(); h.wake()
    r = h.execute({"op": "propose", "agent": "x", "weaknesses": ["high latency", "token overflow"]})
    check("harness propose suggestions", len(r["data"]["suggestions"]) >= 2)
    check("harness never deploys", r["data"]["applied"] is False and r["data"]["requires_approval"])

# --- Bridge agents ----------------------------------------------------------
def test_bridge_degrades_gracefully():
    for B in (OpenCodeBridgeAgent, OpenClawBridgeAgent):
        b = B(); b.wake()
        r = b.execute({"goal": "do something"})
        check(f"bridge {B.__name__} degrades", r["status"] == "error" and "not available" in r["error"])

def test_bridge_is_bridge():
    check("opencode is bridge", issubclass(OpenCodeBridgeAgent, BridgeAgent))
    check("openclaw is bridge", issubclass(OpenClawBridgeAgent, BridgeAgent))

def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try: t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1; print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nV2 architecture tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0
if __name__ == "__main__": raise SystemExit(main())
