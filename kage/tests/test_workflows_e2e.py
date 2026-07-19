"""End-to-end workflow tests: research -> summary -> save (to Obsidian)."""

from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from kage.core.result import ToolResult
from kage.core.workflows.branching import Branch, Retry, Step, Workflow, execute_workflow

_passed = 0; _failed = 0
def check(name, cond):
    global _passed, _failed
    if cond: _passed += 1
    else: _failed += 1; print(f"  FAIL: {name}")

def test_research_summary_save():
    calls = []
    def runner(step, attempt):
        calls.append(step.id)
        if step.action == "vault.save" and not step.input.get("_ok", True):
            return ToolResult.failure("vault write failed")
        return ToolResult.success({"step": step.id, "out": f"{step.action}:done"})
    wf = Workflow(entry="research", steps=[
        Step(id="research", name="Research", agent="browser", action="web.search", input={"query": "ai news"}, next="summary"),
        Step(id="summary", name="Summarize", agent="meta", action="llm.complete", input={"text": "..."},
             branch=Branch(field="status", equals="ok", then_step="save", else_step="notify"), retry=Retry(max_attempts=2, base_delay=0)),
        Step(id="save", name="Save to vault", agent="obsidian", action="vault.save", input={"path": "ai-news.md"}, next=None),
        Step(id="notify", name="Notify failure", agent="discord", action="msg.send", next=None),
    ])
    out = execute_workflow(wf, runner)
    check("e2e success path", out["visited"] == ["research", "summary", "save"])
    check("e2e ok", out["ok"] is True)

def test_summary_failure_halts():
    def runner(step, attempt):
        if step.id == "summary": raise RuntimeError("llm provider down")
        return ToolResult.success({"step": step.id})
    wf = Workflow(entry="research", steps=[
        Step(id="research", name="Research", agent="browser", action="web.search", next="summary"),
        Step(id="summary", name="Summarize", agent="meta", action="llm.complete",
             branch=Branch(field="status", equals="ok", then_step="save", else_step="notify"), retry=Retry(max_attempts=2, base_delay=0)),
        Step(id="save", name="Save", agent="obsidian", action="vault.save", next=None),
        Step(id="notify", name="Notify", agent="discord", action="msg.send", next=None),
    ])
    out = execute_workflow(wf, runner)
    check("e2e halts on failure", out["ok"] is False)
    check("e2e visited research+summary", out["visited"] == ["research", "summary"])
    check("e2e exhausted retries", out["results"]["summary"]["attempts"] == 2)

def test_retry_then_success():
    n = {"i": 0}
    def flaky(step, attempt):
        n["i"] = attempt
        if step.id == "save" and attempt < 2: raise RuntimeError("transient vault error")
        return ToolResult.success({"saved": True})
    wf = Workflow(entry="save", steps=[
        Step(id="save", name="Save", agent="obsidian", action="vault.save", retry=Retry(max_attempts=4, base_delay=0), next=None),
    ])
    out = execute_workflow(wf, flaky)
    check("e2e retry ok", out["ok"] is True)
    check("e2e retry attempts", out["results"]["save"]["attempts"] == 2)

def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try: t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1; print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nE2E workflow tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0
if __name__ == "__main__": raise SystemExit(main())
