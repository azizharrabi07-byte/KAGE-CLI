"""Tests for Phases 3-8 (config/CLI, integrations, workflows, perf/sec/obs).

Run:  python kage/tests/test_phases_3_8.py
  or:  python -m pytest kage/tests/test_phases_3_8.py  (if pytest installed)

These cover the additive Phase 3-8 modules only and depend on the standard
library, so they run without network/transport dependencies installed.
"""

from __future__ import annotations

import os
import sys

# allow `python kage/tests/test_phases_3_8.py` from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from kage.core.result import ToolResult  # noqa: E402
from kage.core import health  # noqa: E402
from kage.core import secrets as secrets_mod  # noqa: E402
from kage.core import observability as obs  # noqa: E402
from kage.core import sandbox  # noqa: E402
from kage.core.workflows.branching import (  # noqa: E402
    Branch, Retry, Step, Workflow, execute_workflow,
)
from kage.cli.repl import run_command  # noqa: E402


_passed = 0
_failed = 0


def check(name, cond):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {name}")


# --- Phase 4: result envelope ----------------------------------------------
def test_result():
    ok = ToolResult.success({"x": 1})
    err = ToolResult.failure("boom")
    check("result.ok true", ok.ok is True)
    check("result.ok false", err.ok is False)
    check("result envelope keys", set(ok.to_dict()) == {"status", "data", "error", "durationMs", "attempts", "meta"})
    check("result error carries message", err.error == "boom")


# --- Phase 4: retry / timeout / health -------------------------------------
def test_health_retry_success():
    attempts = {"n": 0}

    def flaky(attempt):
        attempts["n"] = attempt
        if attempt < 3:
            raise RuntimeError("transient")
        return "done"

    res = health.run_with_retry(flaky, max_attempts=5, base_delay=0)
    check("retry succeeds eventually", res.ok and res.data == "done")
    check("retry records attempts", res.attempts == 3)


def test_health_retry_failure():
    def always_fail(attempt):
        raise RuntimeError("nope")

    res = health.run_with_retry(always_fail, max_attempts=2, base_delay=0)
    check("retry fails when all attempts error", res.ok is False)
    check("retry failure message", "nope" in (res.error or ""))
    check("retry failure attempts", res.attempts == 2)


def test_health_timeout():
    import time

    def slow(attempt):
        time.sleep(0.4)
        return "late"

    res = health.run_with_retry(slow, max_attempts=1, base_delay=0, timeout=0.1)
    check("timeout surfaces as error", res.ok is False)
    check("timeout message", "timeout" in (res.error or "").lower())


def test_health_probe_reconnect():
    calls = {"n": 0}

    def check_fn():
        calls["n"] += 1
        if calls["n"] == 1:
            return ToolResult.failure("down")
        return ToolResult.success("up")

    res = health.probe(check_fn, auto_reconnect=True)
    check("probe reconnects", res.ok is True and res.meta.get("reconnected") is True)


# --- Phase 6: secrets -------------------------------------------------------
def test_secrets():
    secrets_mod.add_secret("DISCORD_BOT_TOKEN", "sk-secret-12345678")
    check("secret resolved from env", secrets_mod.resolve("DISCORD_BOT_TOKEN") == "sk-secret-12345678")
    masked = secrets_mod.mask("sk-secret-12345678")
    check("secret masked hides prefix", masked.endswith("5678") and "secret" not in masked)
    check("secret scrubbed from text", "REDACTED" in secrets_mod.scrub("api_key=abcdefgh1234"))
    recs = {r.key: r for r in secrets_mod.list_secrets()}
    check("secret listed as set", recs["DISCORD_BOT_TOKEN"].set is True)
    check("secret removed", secrets_mod.remove_secret("DISCORD_BOT_TOKEN") is True)
    check("secret gone after remove", secrets_mod.resolve("DISCORD_BOT_TOKEN") is None)


# --- Phase 6: observability -------------------------------------------------
def test_observability():
    obs.reset()
    obs.record_metric("response_time", 100, unit="ms")
    obs.record_metric("response_time", 200, unit="ms")
    obs.add_trace(obs.TraceSpan(agent="discord", action="llm.complete", decision="advance"))
    summary = obs.metric_summary()
    check("metric totals", summary["response_time"]["total"] == 300)
    check("metric count", summary["response_time"]["count"] == 2)
    check("trace recorded", obs.recent_traces(10)[0]["agent"] == "discord")


# --- Phase 6: sandbox -------------------------------------------------------
def test_sandbox():
    ok = sandbox.validate_command("ls -la")
    check("sandbox allows ls", ok.ok and ok.data["command"] == "ls")
    blocked = sandbox.validate_command("rm -rf /")
    check("sandbox blocks rm -rf", blocked.ok is False)
    blocked2 = sandbox.validate_command("curl http://x")
    check("sandbox blocks curl", blocked2.ok is False)
    blocked3 = sandbox.validate_command("cat /etc/passwd")
    check("sandbox blocks absolute path", blocked3.ok is False)
    blocked4 = sandbox.validate_command("nmap localhost")
    check("sandbox blocks unknown command", blocked4.ok is False)
    dry = sandbox.run("echo hi", dry_run=True)
    check("sandbox dry-run no exec", dry.ok and dry.data["executed"] is False)
    real = sandbox.run("echo hello")
    check("sandbox real exec", real.ok and "hello" in real.data["stdout"])


# --- Phase 5: workflow branching + retry -----------------------------------
def test_workflow_branch_then():
    wf = Workflow(
        entry="a",
        steps=[
            Step(id="a", name="A", agent="discord", action="llm.complete",
                 branch=Branch(field="status", equals="ok", then_step="b", else_step="c")),
            Step(id="b", name="B", agent="discord", action="discord.send", next=None),
            Step(id="c", name="C", agent="obsidian", action="obsidian.write", next=None),
        ],
    )
    out = execute_workflow(wf, lambda s, n: ToolResult.success("ok"))
    check("branch takes then-path", out["visited"] == ["a", "b"])


def test_workflow_branch_else():
    wf = Workflow(
        entry="a",
        steps=[
            Step(id="a", name="A", agent="discord", action="llm.complete",
                 branch=Branch(field="status", equals="ok", then_step="b", else_step="c")),
            Step(id="b", name="B", agent="discord", action="discord.send", next=None),
            Step(id="c", name="C", agent="obsidian", action="obsidian.write", next=None),
        ],
    )
    out = execute_workflow(wf, lambda s, n: ToolResult.failure("err"))
    check("branch takes else-path on error", out["visited"] == ["a"])


def test_workflow_retry():
    calls = {"n": 0}

    def flaky(step, attempt):
        calls["n"] = attempt
        if attempt < 3:
            raise RuntimeError("transient")
        return ToolResult.success("ok")

    wf = Workflow(
        entry="x",
        steps=[Step(id="x", name="X", agent="browser", action="browser.navigate",
                    retry=Retry(max_attempts=4, base_delay=0), next=None)],
    )
    out = execute_workflow(wf, flaky)
    check("workflow retry succeeds", out["ok"] is True)
    check("workflow retry attempts", out["results"]["x"]["attempts"] == 3)


# --- Phase 3: CLI -----------------------------------------------------------
def test_cli():
    out = run_command("/version", output="json")
    check("cli /version json", '"version"' in out)
    out = run_command("/providers", output="yaml")
    check("cli /providers yaml", "openai" in out)
    out = run_command("/help")
    check("cli /help lists commands", "/config" in out)
    out = run_command("/shell rm -rf /", output="json", dry_run=True)
    check("cli /shell blocks dangerous", '"error"' in out)
    out = run_command("/workflows", output="json")
    check("cli /workflows runs demo", '"visited"' in out)
    out = run_command("/bogus")
    check("cli unknown command handled", "unknown" in out.lower())


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\nPhases 3-8 tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
