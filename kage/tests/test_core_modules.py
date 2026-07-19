"""Unit tests for core modules (cache, session, memory, tools, engine, config)."""

from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from kage.core.cache import DiskCache
from kage.core.config import Config, load_config, save_config, wizard
from kage.core.memory import MemoryStore
from kage.core.registry import AgentRegistry
from kage.core.security import SecurityPolicy, SecretManager
from kage.core.session import SessionStore
from kage.core.tools.base import ToolRegistry
from kage.core.tools.crew import CrewTool
from kage.core.tools.memory_tool import MemoryTool
from kage.core.workflows.engine import WorkflowEngine

_passed = 0; _failed = 0
def check(name, cond):
    global _passed, _failed
    if cond: _passed += 1
    else: _failed += 1; print(f"  FAIL: {name}")

def test_disk_cache():
    d = DiskCache(root=str(Path(tempfile.mkdtemp()) / "c"))
    check("cache miss", d.get("ns", "k") is None)
    d.set("ns", "k", {"v": 1})
    check("cache hit", d.get("ns", "k") == {"v": 1})
    check("cache clear", d.clear("ns") >= 1)
    check("cache cleared", d.get("ns", "k") is None)

def test_session_store():
    s = SessionStore(db_path=str(Path(tempfile.mkdtemp()) / "s.db"))
    sid = s.create("u1", platform="cli", title="t")
    check("created", sid > 0)
    check("active", s.active("u1") == sid)
    mid = s.add_message(sid, "user", "u1", "hello")
    check("msg added", mid > 0)
    check("history", len(s.history(sid)) == 1)
    check("listed", any(r["id"] == sid for r in s.list("u1")))
    check("resume", s.resume(sid) is True)
    check("end", s.end(sid) is True)
    check("no longer active", s.active("u1") is None)
    s.close()

def test_memory_store():
    m = MemoryStore(root=str(Path(tempfile.mkdtemp()) / "m"))
    check("empty", m.get("u") == {})
    m.set("u", "name", "Kage")
    check("set/get", m.get("u") == {"name": "Kage"})
    check("forget", m.forget("u", "name") is True)
    check("forget missing", m.forget("u", "name") is False)
    m.set("u", "name", "Kage")
    p = m.export_markdown("u")
    check("md export", p.exists() and "Kage" in p.read_text())

def test_memory_tool():
    reg = ToolRegistry()
    m = MemoryStore(root=str(Path(tempfile.mkdtemp()) / "mt"))
    m.set("cli", "city", "Tunis"); reg.register(MemoryTool(m))
    hit = reg.run("memory.recall", {"key": "city"}); miss = reg.run("memory.recall", {"key": "nope"})
    check("tool hit", hit["ok"] and hit["value"] == "Tunis")
    check("tool miss", miss["ok"] is False)

def test_crew_tool():
    from kage.core.base_agent import BaseAgent
    class A(BaseAgent):
        name = kind = "a"
        def wake(self): self._awake = True
        def execute(self, task): return {"ok": True, "agent": self.name}
        def sleep(self): self._awake = False
    reg = AgentRegistry(); reg.register(A)
    crew = CrewTool(reg); out = crew.run({"task": "greet", "agents": ["a"]})
    check("crew ok", out["ok"] and "a" in out["results"])
    check("crew result", out["results"]["a"]["ok"] is True)

def test_workflow_engine():
    tmp = Path(tempfile.mkdtemp()); eng = WorkflowEngine(db_path=str(tmp / "wf.db"))
    wf = tmp / "demo.json"
    wf.write_text(json.dumps({"name": "demo", "steps": [
        {"id": "s1", "action": "noop", "args": {}},
        {"id": "s2", "action": "noop", "args": {}, "depends_on": ["s1"]}]}))
    info = eng.load(str(wf)); wid = info["workflow_id"]
    check("loaded", info["steps"] == 2)
    res = eng.run(wid, lambda step: {"ok": True, "step": step["step_id"]})
    check("ran all", res["results"]["s2"]["ok"] is True)
    check("status rows", len(eng.status(wid)) == 2)

def test_config_roundtrip():
    orig = os.environ.get("HOME"); fake = Path(tempfile.mkdtemp()); os.environ["HOME"] = str(fake)
    try:
        cfg = Config(); cfg.default_user = "tester"; cfg.primary_interface = "telegram"
        p = save_config(cfg); check("saved", p.exists())
        loaded = load_config(); check("loaded", loaded.default_user == "tester")
        check("masks secrets", loaded.to_dict()["llm_api_key"] in ("", "***"))
        check("wizard", wizard(interactive=False).default_user == "tester")
        os.environ["DISCORD_BOT_TOKEN"] = "envtoken"; os.environ["KAGE_USE_TELEGRAM"] = "true"
        env_cfg = load_config()
        check("env token", env_cfg.discord_bot_token == "envtoken")
        check("env bool", env_cfg.use_telegram is True)
        os.environ.pop("DISCORD_BOT_TOKEN", None); os.environ.pop("KAGE_USE_TELEGRAM", None)
    finally: os.environ["HOME"] = orig

def test_security_policy():
    pol = SecurityPolicy()
    check("allow safe", pol.allow("web.search") is True)
    check("deny destructive", pol.allow("shell.run") is False)
    pol.allow_destructive = True
    check("allow destructive", pol.allow("shell.run") is True)
    pol.denied_tools.add("web.fetch")
    check("explicit deny", pol.allow("web.fetch") is False)
    sm = SecretManager(secrets_file=str(Path(tempfile.mkdtemp()) / "sec.json"))
    os.environ["MY_TEST_KEY"] = "val123"
    check("secret env", sm.get("MY_TEST_KEY") == "val123")
    check("secret default", sm.get("NOPE", "d") == "d")
    os.environ.pop("MY_TEST_KEY", None)

def test_registry():
    from kage.core.base_agent import BaseAgent
    class B(BaseAgent):
        name = kind = "bob"
        def wake(self): self._awake = True
        def execute(self, task): return {"ok": True}
        def sleep(self): self._awake = False
    reg = AgentRegistry(); reg.register(B, config={"x": 1})
    check("list", reg.list() == ["bob"])
    check("get", reg.get("bob") is not None)
    a = reg.wake("bob"); check("wake", a.is_awake is True)
    reg.sleep("bob"); check("sleep", a.is_awake is False)
    check("all_info", reg.all_info()[0]["name"] == "bob")
    inst = B(); reg.register_instance(inst); check("instance", reg.get("bob") is inst)

def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try: t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1; print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nCore module tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0
if __name__ == "__main__": raise SystemExit(main())
