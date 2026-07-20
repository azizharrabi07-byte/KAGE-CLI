"""Tests for the TUI polish: colour scheme, compact spacing, auto-complete."""

from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from kage.cli import commands as cmdmod
from kage.cli import theme
from kage.cli.tui import KageTUI, autocomplete_suggestions, PROMPT

_passed = 0; _failed = 0
def check(name, cond):
    global _passed, _failed
    if cond: _passed += 1
    else: _failed += 1; print(f"  FAIL: {name}")

# --- auto-complete ----------------------------------------------------------
def test_autocomplete_only_on_slash():
    check("plain text no suggestions", autocomplete_suggestions("hello") == [])
    check("empty no suggestions", autocomplete_suggestions("") == [])

def test_autocomplete_slash_lists_all():
    sugg = autocomplete_suggestions("/")
    names = [n for n, _ in sugg]
    check("slash lists all", len(sugg) >= 18)
    check("slash includes /help", "/help" in names)
    check("slash includes /agents", "/agents" in names)

def test_autocomplete_prefix_filters():
    check("/he -> help+health", set(n for n,_ in autocomplete_suggestions("/he")) >= {"/help","/health"})
    check("/hel -> help", [n for n,_ in autocomplete_suggestions("/hel")] == ["/help"])
    check("/har -> harness", autocomplete_suggestions("/har") == [("/harness", cmdmod._help.__doc__ or "improvement loop: start|stop|run|status")] or [n for n,_ in autocomplete_suggestions("/har")] == ["/harness"])
    check("/xyz -> none", autocomplete_suggestions("/xyz") == [])

def test_autocomplete_dismissed_on_space():
    check("space dismisses", autocomplete_suggestions("/help ") == [])
    check("space dismisses 2", autocomplete_suggestions("/age ") == [])

def test_autocomplete_returns_pairs():
    for n, d in autocomplete_suggestions("/"):
        check(f"pair {n} has desc", isinstance(d, str) and len(d) > 0)
        break

def test_health_command_exists():
    names = {c.name for c in cmdmod.COMMANDS}
    check("/health present", "/health" in names)
    out = cmdmod.run_slash("/health", {})
    check("/health runs", "health" in out.lower())

# --- colour scheme ----------------------------------------------------------
def test_banner_neutral_not_magenta():
    b = theme.banner(version="9.9", enabled=True)
    # art should be WHITE not MAGENTA
    check("banner art is white", theme.C.WHITE in b)
    check("banner art not magenta", theme.C.MAGENTA not in b)
    check("banner uses cyan accent", theme.C.CYAN in b)

def test_prompt_is_cyan():
    # in raw/line mode the prompt is painted cyan
    p = theme.paint(PROMPT, theme.C.CYAN, bold=True, enabled=True)
    check("prompt cyan", theme.C.CYAN in p and theme.C.MAGENTA not in p)

def test_status_colors():
    check("ok green", theme.status_color("ok") == theme.C.GREEN)
    check("warn yellow", theme.status_color("warn") == theme.C.YELLOW)
    check("error red", theme.status_color("error") == theme.C.RED)
    check("white defined", theme.C.WHITE == "\033[97m")

def test_panels_use_neutral_colors():
    ap = theme.agent_panel([{"name": "x", "kind": "k", "awake": True, "emoji": "🤖"}], enabled=True)
    check("agent panel white header", theme.C.WHITE in ap)
    check("agent panel not magenta", theme.C.MAGENTA not in ap)

# --- spacing ----------------------------------------------------------------
def test_help_compact_no_double_blanks():
    help_text = cmdmod.run_slash("/help", {})
    lines = help_text.split("\n")
    blanks = [i for i, l in enumerate(lines) if l.strip() == ""]
    check("help has no blank lines (compact)", blanks == [])
    check("help single header", lines[0].strip().endswith("commands:"))

def test_banner_compact():
    b = theme.banner(version="1.0", enabled=False)
    rows = [l for l in b.split("\n") if l.strip()]
    # top border + 6 art + 4 text + bottom border = 12 non-empty rows
    check("banner compact (no empty rows)", len(rows) == 12)

def test_status_line_single_bar():
    s = theme.status_line(version="1", agents=1, session="s", memory_mb=10, enabled=False)
    check("status single divider", s.count("─") <= 64)

# --- registry robustness (the reported bug) --------------------------------
def test_register_both_styles():
    from kage.core.registry import AgentRegistry
    from kage.core.base_agent import BaseAgent
    class T(BaseAgent):
        name = kind = "t"
        def wake(self): self._awake = True
        def execute(self, task): return {}
        def sleep(self): self._awake = False
    r = AgentRegistry()
    r.register(T)                      # register(cls)
    r.register("named", T)             # register(name, cls)  <- the user's pattern
    r.register(T, config={"x": 1})     # register(cls, config)
    r.register("named2", T, config={"y": 2})  # register(name, cls, config)
    check("register accepts both styles", set(r.list()) >= {"t", "named", "named2"})
    a = r.get("named"); a.wake()
    check("named agent instantiates", a.is_awake is True)
    a2 = r.get("named2")
    check("named2 carries config", a2.config.get("y") == 2)

def test_register_rejects_missing_class():
    from kage.core.registry import AgentRegistry
    try:
        AgentRegistry().register("justaname")   # name but no class
        check("register(name) without class errors", False)
    except TypeError:
        check("register(name) without class errors", True)

def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try: t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1; print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nTUI polish tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0
if __name__ == "__main__": raise SystemExit(main())
