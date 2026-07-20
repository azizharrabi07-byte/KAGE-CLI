"""cli/completer.py — readline-based slash-command completion.

The robust way to get OpenCode-style autocomplete in a terminal REPL: use the
``readline`` module, which provides as-you-type matching + Tab-to-complete on
top of ``input()`` (works in line mode on Linux/Termux, no raw termios needed).

Only commands starting with ``/`` are completed; plain chat text is untouched.
When readline is unavailable, ``install_completion`` returns False and the
caller falls back to listing commands on a bare ``/``.
"""

from __future__ import annotations

from typing import List, Optional


class SlashCompleter:
    """readline completer delimiting on whitespace and completing ``/commands``."""

    def __init__(self, commands: List[str]) -> None:
        self._commands = sorted(commands)

    def complete(self, text: str, state: int) -> Optional[str]:
        """Called repeatedly by readline with increasing ``state``."""
        if not text.startswith("/"):
            return None
        matches = [c for c in self._commands if c.startswith(text)]
        if state < len(matches):
            return matches[state]
        return None


def install_completion(commands: List[str]) -> bool:
    """Install Tab completion for the given command names. Returns True if active."""
    try:
        import readline  # noqa: F401  (module exists on Linux/Termux/macOS)
    except ImportError:
        return False
    completer = SlashCompleter(commands)
    readline.set_completer(completer.complete)
    # whitespace/newline as token delimiters → a /command is one token
    readline.set_completer_delims(" \t\n")
    try:
        readline.parse_and_bind("tab: complete")
    except Exception:  # noqa: BLE001 — some readline builds reject parse_and_bind
        return False
    return True


def suggestions(prefix: str, commands: List[str], limit: int = 12) -> List[str]:
    """Pure helper: command names matching a ``/``-prefix (no readline needed)."""
    if not prefix.startswith("/"):
        return []
    if prefix == "/":
        return list(sorted(commands))[:limit]
    return [c for c in sorted(commands) if c.startswith(prefix)][:limit]
