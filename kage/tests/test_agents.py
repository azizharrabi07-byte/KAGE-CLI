"""Tests for the real agent implementations (whatsapp, obsidian, system, meta)."""

from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from kage.agents.meta.agent import MetaAgent
from kage.agents.obsidian.agent import ObsidianAgent
from kage.agents.system.agent import SystemAgent
from kage.agents.whatsapp.agent import WhatsAppAgent

_passed = 0; _failed = 0
def check(name, cond):
    global _passed, _failed
    if cond: _passed += 1
    else: _failed += 1; print(f"  FAIL: {name}")

def test_system_health():
    a = SystemAgent(); a.wake(); r = a.execute({"op": "health"})
    check("system health status", r["status"] == "ok")
    d = r["data"]
    check("system battery", "percent" in d["battery"])
    check("system storage free", "free" in d["storage"])
    check("system storage pct", isinstance(d["storage"]["percent_free"], (int, float)))
    check("system cpu cores", d["cpu"]["cores"] >= 1)
    check("system memory total", d["memory"]["total_kb"] >= 0)

def test_system_ops():
    a = SystemAgent(); a.wake()
    check("battery op", a.execute({"op": "battery"})["status"] == "ok")
    check("cpu op", a.execute({"op": "cpu"})["status"] == "ok")
    check("memory op", a.execute({"op": "memory"})["status"] == "ok")
    check("unknown op", a.execute({"op": "nope"})["status"] == "error")

def test_obsidian_degrades():
    os.environ.pop("OBSIDIAN_TOKEN", None)
    a = ObsidianAgent(); a.wake(); r = a.execute({"op": "status"})
    check("obsidian degrades", r["status"] == "error" and "OBSIDIAN_TOKEN" in (r.get("error") or ""))

def test_obsidian_unknown():
    a = ObsidianAgent(); a.wake()
    check("obsidian unknown op", a.execute({"op": "frob"})["status"] == "error")

def test_whatsapp_degrades():
    a = WhatsAppAgent(); a.wake(); r = a.execute({"op": "status"})
    check("whatsapp degrades", r["status"] == "error")

def test_whatsapp_send_no_target():
    a = WhatsAppAgent(); a.wake(); r = a.execute({"op": "send"})
    check("whatsapp send errors", r["status"] == "error")

def test_meta_crew():
    a = MetaAgent(); a.wake(); r = a.execute({"op": "crew"})
    check("meta crew ok", r["status"] == "ok" and "agents" in r["data"])

def test_meta_upgrade_check():
    a = MetaAgent(config={"repo_root": os.getcwd()}); a.wake()
    r = a.execute({"op": "upgrade.check"})
    check("meta upgrade check ok", r["status"] == "ok" and "source" in r["data"])

def test_meta_apply_requires_confirm():
    a = MetaAgent(config={"repo_root": os.getcwd()}); a.wake()
    a.check_upgrade = lambda: {"available": True, "commits_behind": 1}
    r = a.execute({"op": "upgrade.apply", "confirm": False})
    check("meta apply blocked", r["status"] == "error" and "confirm" in (r.get("error") or ""))

def test_meta_unknown():
    a = MetaAgent(); a.wake()
    check("meta unknown op", a.execute({"op": "zzz"})["status"] == "error")

def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try: t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1; print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nAgent tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0
if __name__ == "__main__": raise SystemExit(main())
