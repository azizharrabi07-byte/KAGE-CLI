"""Extra tests lifting core coverage (registry, supervisor, legacy integration, CLI)."""

from __future__ import annotations
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from kage.agents.builtin import BUILTIN_AGENTS
from kage.core.integrations.base import Integration
from kage.core.memory import MemoryStore
from kage.core.registry import AgentRegistry
from kage.core.supervisor import Supervisor
from kage.core.tools.base import ToolRegistry
from kage.core.tools.memory_tool import MemoryTool
from kage.cli.repl import run_command

_passed = 0; _failed = 0
def check(name, cond):
    global _passed, _failed
    if cond: _passed += 1
    else: _failed += 1; print(f"  FAIL: {name}")

def _supervisor(tmp):
    reg = AgentRegistry(); tools = ToolRegistry(); mem = MemoryStore(root=str(tmp / "mem"))
    tools.register(MemoryTool(mem))
    return Supervisor(registry=reg, memory_store=mem, session_store=None, tools=tools)

def test_builtin_roster():
    check("4 agents", len(BUILTIN_AGENTS) == 4)
    check("names", {c.name for c in BUILTIN_AGENTS} == {"whatsapp", "obsidian", "system", "meta"})

def test_registry_discover():
    reg = AgentRegistry()
    reg.discover(["kage.agents.system.agent:SystemAgent"])
    check("discover", "system" in reg.list())
    count = reg.wake_all(); check("wake_all", count >= 1)
    a = reg.get("system"); check("awake", a is not None and a.is_awake is True)
    reg.sleep("system"); check("sleep", a.is_awake is False)

def test_registry_unknown():
    check("unknown", AgentRegistry().get("nope") is None)

def test_supervisor_memory():
    s = _supervisor(Path(tempfile.mkdtemp()))
    resp = s.think("remember my name is Kage")
    check("memory_add", resp.ok is True)
    check("stored", "Kage" in str(s.memory.get("cli").get("name", "")))
    check("recall", s.think("what is my name?").ok is True)

def test_supervisor_agents():
    s = _supervisor(Path(tempfile.mkdtemp())); s.registry.register(BUILTIN_AGENTS[2])
    check("agent_list", s.think("list agents").ok is True)

def test_supervisor_help():
    s = _supervisor(Path(tempfile.mkdtemp()))
    check("help", s.think("/help").ok is True)

def test_legacy_integration():
    class Flaky(Integration):
        name = "flaky"
        def connect(self): self._connected = True
        def health_check(self): return self._connected
    it = Flaky(retries=3, backoff=0); it.connect()
    check("connect", it.connected is True)
    check("health", it.health_check() is True)
    try: it.call(lambda: (_ for _ in ()).throw(RuntimeError("nope"))); check("raises", False)
    except ConnectionError: check("raises", True)

def test_cli():
    check("config get", "default_user" in run_command("/config get default_user", output="json"))
    check("health json", '"attempts"' in run_command("/health", output="json"))
    check("models yaml", "gpt" in run_command("/models", output="yaml"))
    check("agents runs", isinstance(run_command("/agents", output="text"), str))

def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try: t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1; print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nCoverage-boost tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0
if __name__ == "__main__": raise SystemExit(main())
