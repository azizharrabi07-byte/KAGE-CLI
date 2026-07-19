"""Tests for the supervisor brain (intent, memory, routing).

Run:  python -m kage.tests.test_supervisor
  or:  python -m pytest kage/tests/test_supervisor.py  (if pytest installed)
"""

from __future__ import annotations

import os
import sys

# allow `python kage/tests/test_supervisor.py` from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from kage.core.supervisor import (  # noqa: E402
    Supervisor, detect_intent, parse_memory_add, recall_memory,
)
from kage.core.registry import AgentRegistry  # noqa: E402
from kage.core.memory import MemoryStore  # noqa: E402


def _supervisor(tmp_path) -> Supervisor:
    reg = AgentRegistry()
    return Supervisor(registry=reg, memory_store=MemoryStore(root=str(tmp_path / "mem")))


def test_intent_detection() -> None:
    assert detect_intent("remember my name is Daddy") == "memory_add"
    assert detect_intent("what is my name?") == "memory_recall"
    assert detect_intent("search the latest AI news") == "search"
    assert detect_intent("research AI trends") == "research"
    assert detect_intent("list all agents") == "agent_list"
    assert detect_intent("system health") == "system"
    assert detect_intent("hello there") == "greeting"
    assert detect_intent("help me") == "help"
    assert detect_intent("tell me a joke") == "chat"


def test_memory_add_parse() -> None:
    assert parse_memory_add("remember my name is Daddy") == {"key": "name", "value": "Daddy"}
    assert parse_memory_add("memory add role Founder") == {"key": "role", "value": "Founder"}
    assert parse_memory_add("call me Boss") == {"key": "name", "value": "Boss"}


def test_memory_recall() -> None:
    mem = {"name": "Daddy", "likes": "espresso"}
    assert recall_memory(mem, "what is my name?") == "Daddy"
    assert recall_memory(mem, "who am i") == "Daddy"
    assert recall_memory({}, "what is my name?") is None


def test_supervisor_memory_roundtrip(tmp_path) -> None:
    sup = _supervisor(tmp_path)
    uid = "u1"
    add = sup.think("remember my name is Daddy", user_id=uid)
    assert add.intent == "memory_add"
    assert "Daddy" in add.text
    rec = sup.think("what is my name?", user_id=uid)
    assert rec.intent == "memory_recall"
    assert "Daddy" in rec.text


def test_supervisor_routing(tmp_path) -> None:
    sup = _supervisor(tmp_path)
    assert sup.think("search ai news").agent == "Whiz"
    assert sup.think("research quantum computing").agent == "Sage"
    assert sup.think("system status").agent == "Sentinel"
    assert sup.think("agents list").intent == "agent_list"


# --- plain-python runner (no pytest needed) -------------------------------
def _run_all() -> int:
    import tempfile
    failures = 0
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        import inspect
        params = inspect.signature(test).parameters
        try:
            if params:
                with tempfile.TemporaryDirectory() as d:
                    from pathlib import Path
                    test(Path(d))
            else:
                test()
            print(f"  PASS  {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"  FAIL  {test.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  ERROR {test.__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
