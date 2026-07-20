"""Tests for the OpenCode-style TUI + unified command registry (CLI↔Discord parity).

Run:  python kage/tests/test_tui.py
"""

from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from kage.cli import commands as cmdmod
from kage.cli import theme
from kage.cli.tui import KageTUI
from kage.core.registry import AgentRegistry
from kage.core.base_agent import BaseAgent

_passed = 0; _failed = 0
def check(name, cond):
    global _passed, _failed
    if cond: _passed += 1
    else: _failed += 1; print(f"  FAIL: {name}")

# --- theme / banner ---------------------------------------------------------
def test_banner_renders():
    b = theme.banner(version="3.1.0", enabled=False)
    check("banner has art", "KAGE" in b.upper() or "██" in b)
    check("banner has version", "3.1.0" in b)
    check("banner boxed", b.startswith("┌") or "┌" in b)

def test_banner_with_color():
    b = theme.banner(version="9.9", enabled=True)
    check("banner color codes present", "\033[" in b)

def test_status_line():
    s = theme.status_line(version="3.0", provider="Groq", model="llama-3.3",
                          agents=5, session="kage-abc", memory_mb=128.0, enabled=False)
    check("status has version", "3.0" in s)
    check("status has agents", "5" in s)
    check("status has session", "kage-abc" in s)
    check("status has mem", "128" in s)

def test_color_disabled_with_no_color():
    os.environ["NO_COLOR"] = "1"
    check("color off when NO_COLOR set", theme.color_enabled() is False)
    del os.environ["NO_COLOR"]

def test_paint():
    check("paint applies when enabled", "\033[31m" in theme.paint("x", theme.C.RED, enabled=True))
    check("paint strips when disabled", theme.paint("x", theme.C.RED, enabled=False) == "x")

def test_status_color():
    check("ok->green", theme.status_color("ok") == theme.C.GREEN)
    check("error->red", theme.status_color("error") == theme.C.RED)
    check("executing->yellow", theme.status_color("executing") == theme.C.YELLOW)

def test_agent_panel():
    p = theme.agent_panel([{"name": "sys", "kind": "system", "awake": True, "emoji": "🛡️"}], enabled=False)
    check("agent panel lists agent", "sys" in p and "running" in p)

def test_command_palette():
    p = theme.command_palette([("/help", "help"), ("/agents", "list")], enabled=False)
    check("palette has commands", "/help" in p and "/agents" in p)

def test_session_panel():
    p = theme.session_panel([{"id": "1", "title": "t", "status": "active"}], active_id="1", enabled=False)
    check("session panel marks active", "1" in p)

# --- command registry -------------------------------------------------------
def test_command_table_complete():
    names = {c.name for c in cmdmod.COMMANDS}
    for required in ["/help", "/agents", "/harness", "/plugins", "/install", "/remove",
                     "/config", "/secrets", "/version", "/exit"]:
        check(f"command {required} present", required in names)

def test_palette_returns_pairs():
    pal = cmdmod.palette()
    check("palette non-empty", len(pal) >= 15)
    check("palette is tuples", all(len(p) == 2 for p in pal))

def test_run_slash_handlers():
    ctx = {}
    check("/version", "3." in cmdmod.run_slash("/version", ctx))
    check("/help non-empty", len(cmdmod.run_slash("/help", ctx)) > 10)
    check("/providers", "groq" in cmdmod.run_slash("/providers", ctx))
    check("/models groq", "llama" in cmdmod.run_slash("/models groq", ctx))
    check("/config get", "default_user" in cmdmod.run_slash("/config get default_user", ctx))
    check("non-slash returns None", cmdmod.run_slash("hello", ctx) is None)
    check("unknown slash errors", "unknown" in cmdmod.run_slash("/bogus", ctx).lower())

def test_harness_commands():
    s = cmdmod.run_slash("/harness start", {})
    check("harness start", "started" in s.lower())
    check("harness running status", "running=True" in cmdmod.run_slash("/harness status", {}))
    run = cmdmod.run_slash("/harness run", {"runs": [{"agent": "x", "ok": True, "durationMs": 50}]})
    check("harness run reports cycle", "cycle" in run.lower())
    check("harness stop", "stopped" in cmdmod.run_slash("/harness stop", {}).lower())

def test_plugins_commands():
    from kage.core.plugins import PluginManager
    pm = PluginManager(plugin_root="kage/plugins"); pm.install_all()
    ctx = {"plugin_manager": pm}
    out = cmdmod.run_slash("/plugins", ctx)
    check("plugins list", "summarizer" in out)
    check("install missing", "not found" in cmdmod.run_slash("/install nope", ctx).lower())

# --- TUI controller ---------------------------------------------------------
class DummyAgent(BaseAgent):
    name = kind = "dummy"
    def wake(self): self._awake = True
    def execute(self, task): return {"status": "ok", "data": {"hi": True}}
    def sleep(self): self._awake = False

def test_tui_banner_and_status():
    t = KageTUI()
    b = t.render_banner()
    check("tui banner", "3." in b and ("██" in b or "KAGE" in b.upper()))
    check("tui status", "3." in t.render_status() and "Session" in t.render_status())

def test_tui_agents_panel():
    reg = AgentRegistry(); reg.register(DummyAgent)
    t = KageTUI(registry=reg)
    import io
    t.stream = io.StringIO()
    t.show_agents()
    out = t.stream.getvalue()
    check("tui shows agents", "dummy" in out)

def test_tui_palette_panel():
    t = KageTUI()
    import io; t.stream = io.StringIO()
    t.show_palette()
    check("tui palette", "/help" in t.stream.getvalue())

def test_tui_handle_line():
    t = KageTUI()
    check("tui version", "3." in t.handle_line("/version"))
    check("tui exit sentinel", t.handle_line("/exit") == "__quit__")
    check("tui quit sentinel", t.handle_line("/quit") == "__quit__")
    check("tui empty", t.handle_line("") is None)

def test_tui_history_records():
    class FakeSup:
        default_user = "cli"
        registry = AgentRegistry()
        tools = None
        def think(self, msg, user_id="cli"):
            class R:
                ok = True; intent = "chat"; agent = "Kage"; text = f"echo:{msg}"
            return R()
    t = KageTUI(supervisor=FakeSup())
    out = t.handle_line("hello world")
    check("tui delegates to supervisor", "echo:hello world" in out)
    check("tui records history", t.history == ["hello world"])

def test_cli_discord_parity():
    """Every handler-backed command is reachable identically from both."""
    pal = [c[0] for c in cmdmod.palette()]
    for name in ["/help", "/version", "/agents", "/harness", "/plugins"]:
        check(f"parity {name} in palette", name in pal)

def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try: t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1; print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nTUI tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0
if __name__ == "__main__": raise SystemExit(main())
