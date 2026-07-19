"""Tests for the action execution layer (parse + executor + supervisor wiring).

Run:  python kage/tests/test_actions.py
  or: python -m pytest kage/tests/test_actions.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from kage.core.actions import (  # noqa: E402
    ACTION_SCHEMA, Action, ActionExecutor, format_results, parse_actions,
)
from kage.core.memory import MemoryStore  # noqa: E402
from kage.core.registry import AgentRegistry  # noqa: E402
from kage.core.supervisor import Supervisor  # noqa: E402

_passed = 0
_failed = 0


def check(name, cond):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {name}")


def _sup(tmp: Path, *, llm=None, allow_all=False) -> Supervisor:
    reg = AgentRegistry()
    return Supervisor(registry=reg, memory_store=MemoryStore(root=str(tmp / "m")),
                      config={"root": str(tmp), "allow_destructive": allow_all}, llm=llm)


# --- parse_actions ----------------------------------------------------------
def test_parse_fenced_json():
    acts, disp = parse_actions('Sure!\n```json\n{"action": "shell", "command": "ls"}\n```')
    check("fenced: one action", len(acts) == 1 and acts[0].kind == "shell")
    check("fenced: command extracted", acts[0].params.get("command") == "ls")
    check("fenced: display strips block", "```" not in disp and "Sure!" in disp)


def test_parse_bare_json():
    acts, disp = parse_actions('doing it {"action":"reply","text":"hi"} done')
    check("bare: one action", len(acts) == 1 and acts[0].kind == "reply")
    check("bare: stripped from display", "{" not in disp)


def test_parse_array():
    acts, _ = parse_actions('```json\n[{"action":"reply","text":"a"},{"action":"reply","text":"b"}]\n```')
    check("array: two actions", len(acts) == 2)


def test_parse_no_action():
    acts, disp = parse_actions("just a normal chat reply, no json")
    check("no action: empty", acts == [])
    check("no action: text intact", disp == "just a normal chat reply, no json")


def test_parse_nested_json():
    payload = '{"action":"file_write","path":"a.md","content":"{ \\"nested\\": true }"}'
    acts, _ = parse_actions(payload)
    check("nested braces parse", len(acts) == 1 and acts[0].kind == "file_write")
    check("nested content intact", "nested" in acts[0].params.get("content", ""))


# --- executor: shell --------------------------------------------------------
def test_shell_allowed():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    r = ex.execute(Action("shell", {"command": "echo kage-alive"}))
    check("shell runs", r["ok"] is True and "kage-alive" in r["stdout"])


def test_shell_exit_code():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    r = ex.execute(Action("shell", {"command": "false"}))
    check("shell captures nonzero exit", r["ok"] is False and r["exit_code"] != 0)


def test_shell_dangerous_needs_confirm():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    r = ex.execute(Action("shell", {"command": "rm -rf /"}))
    check("rm -rf / needs confirm", r.get("status") == "needs_confirmation" and r["ok"] is False)


def test_shell_force_push_gated():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    r = ex.execute(Action("shell", {"command": "git push --force origin main"}))
    check("force push gated", r.get("status") == "needs_confirmation")


def test_shell_normal_push_runs():
    # non-force git push must run immediately (cwd is an empty temp dir, so it
    # errors at the git level, but the executor must ATTEMPT it, not gate it)
    ex = ActionExecutor(root=tempfile.mkdtemp())
    r = ex.execute(Action("shell", {"command": "git status"}))
    check("normal git command runs (not gated)", r.get("status") is None)


def test_shell_allow_all_bypasses_dangerous():
    ex = ActionExecutor(root=tempfile.mkdtemp(), allow_all=True)
    r = ex.execute(Action("shell", {"command": "echo allowed"}))
    check("allow_all runs command", r["ok"] is True)


def test_shell_empty():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    check("empty cmd errors", ex.execute(Action("shell", {"command": ""}))["ok"] is False)


# --- executor: file_write ---------------------------------------------------
def test_file_write_create_append_overwrite():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    r = ex.execute(Action("file_write", {"path": "notes.md", "content": "line1\n"}))
    check("create ok", r["ok"] and r["mode"] == "create")
    r2 = ex.execute(Action("file_write", {"path": "notes.md", "content": "line2\n", "mode": "append"}))
    check("append ok", r2["ok"])
    text = (Path(ex.root) / "notes.md").read_text()
    check("append content correct", text == "line1\nline2\n")
    r3 = ex.execute(Action("file_write", {"path": "notes.md", "content": "x", "mode": "overwrite"}))
    check("overwrite ok", r3["ok"] and (Path(ex.root) / "notes.md").read_text() == "x")


def test_file_write_create_existing_errors():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    ex.execute(Action("file_write", {"path": "f.md", "content": "a"}))
    r = ex.execute(Action("file_write", {"path": "f.md", "content": "b"}))
    check("create existing blocked", r["ok"] is False and "exists" in r["error"])


def test_file_write_traversal_blocked():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    r = ex.execute(Action("file_write", {"path": "../../escape.md", "content": "x"}))
    check("traversal blocked", r["ok"] is False)


def test_file_write_nested_dirs():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    r = ex.execute(Action("file_write", {"path": "deep/nested/file.md", "content": "x"}))
    check("nested dirs created", r["ok"] and (Path(ex.root) / "deep/nested/file.md").exists())


# --- executor: create_agent -------------------------------------------------
def test_create_agent_scaffolds():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    # need a kage/agents dir layout; create a minimal package root
    (Path(ex.root) / "kage" / "agents").mkdir(parents=True)
    r = ex.execute(Action("create_agent", {"name": "weather", "description": "reports weather", "emoji": "🌧️"}))
    check("create_agent ok", r["ok"] and r["name"] == "weather")
    agent_file = Path(ex.root) / "kage" / "agents" / "weather" / "agent.py"
    check("agent.py written", agent_file.exists())
    check("template has class", "class WeatherAgent" in agent_file.read_text())
    check("register hint", "kage.agents.weather.agent:WeatherAgent" in r["register"])


def test_create_agent_duplicate():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    (Path(ex.root) / "kage" / "agents").mkdir(parents=True)
    ex.execute(Action("create_agent", {"name": "x"}))
    r = ex.execute(Action("create_agent", {"name": "x"}))
    check("duplicate blocked", r["ok"] is False)


def test_create_agent_bad_name():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    # a name that sanitizes to empty must be rejected
    r = ex.execute(Action("create_agent", {"name": "@#$%"}))
    check("empty-after-sanitize rejected", r["ok"] is False)
    # a name with junk is sanitized to a valid slug (not rejected)
    ex2 = ActionExecutor(root=tempfile.mkdtemp())
    (Path(ex2.root) / "kage" / "agents").mkdir(parents=True)
    r2 = ex2.execute(Action("create_agent", {"name": "Weather Bot!"}))
    check("junk name sanitized to slug", r2["ok"] and r2["name"] == "weatherbot")


def test_unknown_action():
    ex = ActionExecutor(root=tempfile.mkdtemp())
    r = ex.execute(Action("frobnicate", {}))
    check("unknown action errors", r["ok"] is False and "unknown" in r["error"])


def test_format_results():
    out = format_results([{"ok": True, "kind": "shell", "command": "echo hi", "exit_code": 0, "stdout": "hi\n"}])
    check("format includes command", "echo hi" in out)
    check("format includes output", "hi" in out)


# --- supervisor integration (LLM emits action) -----------------------------
def test_supervisor_executes_llm_action():
    tmp = Path(tempfile.mkdtemp())
    def fake_llm(message, context=""):
        return f'Sure!\n```json\n{{"action":"shell","command":"echo {message}"}}\n```'
    sup = _sup(tmp, llm=fake_llm)
    resp = sup.think("kage-test", user_id="u")
    check("llm action executed", resp.side_effects and resp.side_effects[0]["kind"] == "shell")
    check("result folded into text", "kage-test" in resp.text)


def test_supervisor_plain_llm_reply():
    tmp = Path(tempfile.mkdtemp())
    def fake_llm(message, context=""):
        return "Just chatting, no action needed."
    sup = _sup(tmp, llm=fake_llm)
    resp = sup.think("explain photosynthesis", user_id="u")
    check("plain reply, no actions", resp.side_effects == [])
    check("plain reply text intact", resp.text == "Just chatting, no action needed.")


def test_supervisor_rule_based_list_files():
    """No LLM: 'list files' should trigger a shell ls action."""
    tmp = Path(tempfile.mkdtemp())
    (tmp / "hello.txt").write_text("x")
    sup = _sup(tmp)
    resp = sup.think("list files in this folder", user_id="u")
    check("rule-based list files acted", bool(resp.side_effects))
    check("rule-based ls output", "hello.txt" in resp.text)


def test_supervisor_rule_based_create_agent():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "kage" / "agents").mkdir(parents=True)
    sup = _sup(tmp)
    resp = sup.think("create a new agent called weather", user_id="u")
    fx = next((f for f in resp.side_effects if f["kind"] == "create_agent"), None)
    check("rule-based create agent acted", fx is not None and fx["ok"])
    check("rule-based agent file scaffolded", (tmp / "kage" / "agents" / "weather" / "agent.py").exists())
    check("rule-based agent register hint", fx["register"].endswith(":WeatherAgent"))


def test_supervisor_chat_unaffected():
    """Normal chat without LLM still returns the friendly fallback."""
    tmp = Path(tempfile.mkdtemp())
    sup = _sup(tmp)
    resp = sup.think("tell me a joke", user_id="u")
    check("normal chat no side effects", resp.side_effects == [])
    check("normal chat fallback text", "got it" in resp.text.lower())


def test_action_schema_present():
    check("schema documents actions", "shell" in ACTION_SCHEMA and "create_agent" in ACTION_SCHEMA)


def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1
            print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nAction tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
