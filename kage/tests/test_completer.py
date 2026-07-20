"""Tests for readline completion + polished REPL prompt/autocomplete.

Run:  python kage/tests/test_completer.py
"""

from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from kage.cli.completer import SlashCompleter, install_completion, suggestions
from kage.cli.commands import command_names
from kage.cli.repl import REPL, PROMPT_C
from kage.cli import theme

_passed = 0; _failed = 0
def check(name, cond):
    global _passed, _failed
    if cond: _passed += 1
    else: _failed += 1; print(f"  FAIL: {name}")

# --- completer logic --------------------------------------------------------
def test_suggestions_slash_only():
    cmds = ["/help", "/agents", "/health", "/harness", "/exit"]
    check("plain text no suggestions", suggestions("hello", cmds) == [])
    check("empty no suggestions", suggestions("", cmds) == [])

def test_suggestions_all_on_slash():
    cmds = ["/help", "/agents", "/health"]
    check("slash lists all", set(suggestions("/", cmds)) == {"/help", "/agents", "/health"})

def test_suggestions_prefix_filter():
    cmds = ["/help", "/health", "/harness", "/agents"]
    check("/he -> help+health", set(suggestions("/he", cmds)) == {"/help", "/health"})
    check("/hel -> help only", suggestions("/hel", cmds) == ["/help"])
    check("/xyz -> none", suggestions("/xyz", cmds) == [])

def test_suggestions_limit():
    cmds = [f"/cmd{i}" for i in range(20)]
    check("limit respected", len(suggestions("/", cmds, limit=5)) == 5)

def test_completer_state_iteration():
    c = SlashCompleter(["/help", "/health", "/agents"])
    check("state 0", c.complete("/he", 0) == "/health")
    check("state 1", c.complete("/he", 1) == "/help")
    check("state 2 exhausted", c.complete("/he", 2) is None)
    check("non-slash -> None", c.complete("hello", 0) is None)

def test_install_completion_runs():
    # Should return a bool without raising (True if readline present).
    result = install_completion(["/help", "/exit"])
    check("install returns bool", isinstance(result, bool))

# --- command_names ----------------------------------------------------------
def test_command_names_populated():
    names = command_names()
    check("command_names non-empty", len(names) >= 15)
    check("includes /help", "/help" in names)
    check("includes /agents", "/agents" in names)

# --- polished REPL ----------------------------------------------------------
def test_repl_banner_has_version():
    r = REPL()
    b = r.banner()
    check("banner has version", "3." in b)

def test_repl_suggestion_block():
    r = REPL()
    block = r._suggestion_block("/he")
    check("suggestion block lists matches", "/help" in block and "/health" in block)
    empty = r._suggestion_block("/zzz")
    check("no-match suggestion", "no matching" in empty)

def test_repl_handle():
    r = REPL()
    check("handle /version", "3." in r.handle("/version"))
    check("handle /exit sentinel", r.handle("/exit") == "__exit__")
    check("handle blank -> None", r.handle("   ") is None)

def test_prompt_is_cyan_not_magenta():
    p = theme.paint(PROMPT_C, theme.C.CYAN, bold=True, enabled=True)
    check("prompt cyan", theme.C.CYAN in p)
    check("prompt not magenta", theme.C.MAGENTA not in p)

# --- cyan theme across panels ----------------------------------------------
def test_theme_neutral_palette():
    b = theme.banner(version="1.0", enabled=True)
    check("banner white chrome", theme.C.WHITE in b)
    check("banner no magenta", theme.C.MAGENTA not in b)
    check("status ok green", theme.status_color("ok") == theme.C.GREEN)
    check("status error red", theme.status_color("error") == theme.C.RED)

def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try: t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1; print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nCompleter/REPL tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0
if __name__ == "__main__": raise SystemExit(main())
