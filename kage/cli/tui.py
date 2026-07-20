"""cli/tui.py — OpenCode-style terminal REPL for KAGE.

Features:
  • ASCII banner + compact status line
  • Tab → agent panel · Ctrl+P → command palette · Ctrl+F → sessions
  • **Live command auto-complete**: typing ``/`` shows matching commands that
    filter as you type; ↑↓ to move, Tab to complete, Enter to run, Space/Esc to
    dismiss. (Only in raw mode, i.e. a real terminal.)
  • Cyan prompt, white text, green/yellow/red status — auto-disabled when piped
  • Full CLI ↔ Discord parity via the unified command registry

Input uses raw terminal mode (termios/tty) on POSIX/Termux; degrades to plain
line input when stdin is not a TTY (CI/pipe/test).
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from .. import __version__
from . import commands as cmdmod
from .theme import (C, agent_panel, banner, clear_screen, color_enabled,
                    command_palette, paint, session_panel, status_color, status_line,
                    visible_len)

# Special key codes (Ctrl+X = chr(x & 0x1f)).
KEY_TAB = "\t"
KEY_CTRL_P = "\x10"
KEY_CTRL_F = "\x06"
KEY_CTRL_L = "\x0c"
KEY_CTRL_C = "\x03"
KEY_CTRL_D = "\x04"
KEY_ESC = "\x1b"
KEY_ENTER = "\r"
KEY_NL = "\n"
KEY_BACKSPACE = "\x7f"

PROMPT = "kage❯ "
MAX_SUGGESTIONS = 8


def autocomplete_suggestions(buf: str) -> List[tuple]:
    """Return ``(name, desc)`` commands matching the current ``/``-prefix.

    Pure function (unit-tested): shows all commands for ``/``, filters by prefix
    for ``/he`` etc., and returns ``[]`` for non-slash input or input with a
    space (so suggestions vanish once the user types arguments).
    """
    if not buf.startswith("/") or " " in buf:
        return []
    palette = cmdmod.palette()
    if buf == "/":
        return list(palette)
    return [(n, d) for (n, d) in palette if n.startswith(buf)]


class KageTUI:
    """The OpenCode-style REPL controller."""

    def __init__(self, supervisor: Any = None, *, registry: Any = None,
                 tool_manager: Any = None, plugin_manager: Any = None,
                 sessions: Any = None, stream=None) -> None:
        self.supervisor = supervisor
        self.registry = registry or getattr(supervisor, "registry", None)
        self.tool_manager = tool_manager or getattr(supervisor, "tools", None)
        self.plugin_manager = plugin_manager
        self.sessions = sessions
        self.session_id = "kage-default"
        self.stream = stream or sys.stdout
        self.history: List[str] = []

    # -- context -------------------------------------------------------------
    def ctx(self) -> Dict[str, Any]:
        return {"registry": self.registry, "tool_manager": self.tool_manager,
                "plugin_manager": self.plugin_manager, "sessions": self.sessions,
                "default_user": getattr(self.supervisor, "default_user", "cli")}

    # -- rendering -----------------------------------------------------------
    def print(self, text: str = "") -> None:
        self.stream.write(text + "\n")
        self.stream.flush()

    def render_banner(self) -> str:
        return banner(version=__version__)

    def render_status(self) -> str:
        providers = {"groq": "Groq", "openai": "OpenAI"}.get(
            os.environ.get("LLM_PROVIDER", "groq").lower(),
            os.environ.get("LLM_PROVIDER", "Groq"))
        model = os.environ.get("LLM_MODEL", "llama-3.3-70b")
        n_agents = len(self.registry.list()) if self.registry else 0
        return status_line(version=__version__, provider=providers, model=model,
                           agents=n_agents, session=self.session_id, memory_mb=_mem_mb())

    def show_agents(self) -> None:
        self.print(agent_panel(self.registry.all_info() if self.registry else []))

    def show_palette(self) -> None:
        self.print(command_palette(cmdmod.palette()))

    def show_sessions(self) -> None:
        rows = []
        if self.sessions:
            try:
                for r in self.sessions.list(self.ctx()["default_user"]):
                    rows.append({"id": str(r["id"]), "title": r.get("title", ""),
                                 "status": r.get("status", "")})
            except Exception:  # noqa: BLE001
                pass
        if not rows:
            rows = [{"id": self.session_id, "title": "current", "status": "active"}]
        self.print(session_panel(rows, active_id=self.session_id))

    # -- message handling ----------------------------------------------------
    def handle_line(self, line: str) -> Optional[str]:
        """Process one input line. Returns text to display, or None to skip."""
        line = line.strip()
        if not line:
            return None
        if line in ("/exit", "/quit"):
            return "__quit__"
        out = cmdmod.run_slash(line, self.ctx())
        if out is not None:
            return out
        if self.supervisor is None:
            return paint("(no supervisor connected)", C.YELLOW)
        msg = line[1:] if line.startswith("/") else line
        self.history.append(msg)
        resp = self.supervisor.think(msg, user_id=self.ctx()["default_user"])
        head = paint(f"{getattr(resp, 'agent', 'Kage')} · {resp.intent}",
                     status_color("ok" if resp.ok else "error"), bold=True)
        return f"{head}\n{resp.text}"

    # -- main loop -----------------------------------------------------------
    def run(self) -> int:
        clear_screen()
        self.print(self.render_banner())
        interactive = sys.stdin.isatty() and sys.stdout.isatty()
        if interactive:
            return self._loop_raw()
        return self._loop_line()

    def _loop_line(self) -> int:
        """Line-based loop with readline Tab-completion for /commands."""
        from .completer import install_completion, suggestions
        install_completion(cmdmod.command_names())
        self.print(paint("KAGE REPL (line mode) — /help, /exit", C.DIM))
        while True:
            try:
                line = input(paint(PROMPT, C.CYAN, bold=True))
            except (EOFError, KeyboardInterrupt):
                self.print()
                return 0
            # nicety: bare "/" lists all commands
            if line.strip() == "/":
                self.print(self._suggestions_block("/"))
                continue
            out = self.handle_line(line)
            if out == "__quit__":
                self.print(paint("bye 👋", C.CYAN))
                return 0
            if out is not None:
                self.print(out)

    # ---- raw mode (real TTY) ----------------------------------------------
    def _loop_raw(self) -> int:  # pragma: no cover - needs a real TTY
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        buf = ""
        self._sugg_idx = 0
        try:
            tty.setraw(fd)
            self._draw(buf)
            while True:
                key = self._read_key()
                if key in (KEY_CTRL_C, KEY_CTRL_D):
                    self._newline()
                    self._w(paint("bye 👋", C.CYAN) + "\n")
                    return 0
                if key == KEY_CTRL_L:
                    clear_screen(); self._draw(buf); continue
                if key in ("UP", "DOWN") and autocomplete_suggestions(buf):
                    sugg = autocomplete_suggestions(buf)
                    if key == "UP":
                        self._sugg_idx = (self._sugg_idx - 1) % len(sugg)
                    else:
                        self._sugg_idx = (self._sugg_idx + 1) % len(sugg)
                    self._draw(buf); continue
                if key == KEY_TAB:
                    sugg = autocomplete_suggestions(buf)
                    if sugg:
                        buf = sugg[self._sugg_idx % len(sugg)][0] + " "
                        self._draw(buf)
                    else:
                        self._show_panel(self._agents_panel_text()); self._draw(buf)
                    continue
                if key == KEY_CTRL_P:
                    self._show_panel(command_palette(cmdmod.palette())); self._draw(buf); continue
                if key == KEY_CTRL_F:
                    self._show_panel(self._sessions_panel_text()); self._draw(buf); continue
                if key in (KEY_ENTER, KEY_NL):
                    self._newline()
                    run = buf
                    sugg = autocomplete_suggestions(buf)
                    if sugg and buf not in [n for n, _ in sugg]:
                        run = sugg[self._sugg_idx % len(sugg)][0]
                    out = self.handle_line(run)
                    if out == "__quit__":
                        self._w(paint("bye 👋", C.CYAN) + "\n"); return 0
                    if out is not None:
                        self._w(out + "\n")
                    buf = ""
                    self._draw(buf)
                    continue
                if key in (KEY_ESC, "ESC"):
                    buf = ""; self._draw(buf); continue
                if key == KEY_BACKSPACE:
                    buf = buf[:-1]; self._draw(buf); continue
                if key == " ":
                    buf += " "; self._draw(buf); continue
                if isinstance(key, str) and len(key) == 1 and key.isprintable():
                    buf += key
                    # reset highlight when the prefix changes
                    self._sugg_idx = 0
                    self._draw(buf)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def _read_key(self) -> str:  # pragma: no cover - needs a real TTY
        """Read one key; decode arrow keys; return 'UP'/'DOWN'/'ESC' or the char."""
        import select
        ch = sys.stdin.read(1)
        if ch == KEY_ESC:
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if ready:
                nxt = sys.stdin.read(1)
                if nxt == "[":
                    code = sys.stdin.read(1)
                    if code == "A":
                        return "UP"
                    if code == "B":
                        return "DOWN"
                return "ESC"
            return "ESC"
        return ch

    def _draw(self, buf: str) -> None:  # pragma: no cover - needs a real TTY
        """Redraw the prompt line + live auto-complete suggestions below it."""
        # Clear from the start of the prompt line to end of screen.
        self.stream.write("\r\033[J")
        prompt = paint(PROMPT, C.CYAN, bold=True)
        self.stream.write(prompt + buf)
        sugg = autocomplete_suggestions(buf)
        shown = sugg[:MAX_SUGGESTIONS]
        if self._sugg_idx >= max(len(shown), 1):
            self._sugg_idx = 0
        for i, (cmd, desc) in enumerate(shown):
            sel = i == self._sugg_idx
            marker = paint("▸ ", C.CYAN, bold=True) if sel else "  "
            name = paint(cmd, C.CYAN, bold=True) if sel else paint(cmd, C.WHITE)
            self.stream.write("\n\r" + marker + name + "  " + paint(desc, C.GRAY))
        if shown:
            # move cursor back up to the prompt line, then to end of buffer
            self.stream.write(f"\033[{len(shown)}A\r")
            col = visible_len(prompt) + len(buf)
            if col > 0:
                self.stream.write(f"\033[{col}C")
        self.stream.flush()

    def _newline(self) -> None:  # pragma: no cover
        self.stream.write("\r\033[J")  # clear prompt + suggestions
        self.stream.flush()

    def _w(self, text: str) -> None:  # pragma: no cover
        self.stream.write(text)
        self.stream.flush()

    def _show_panel(self, text: str) -> None:  # pragma: no cover
        self.stream.write("\r\033[J" + text + "\n")
        self.stream.flush()

    def _suggestions_block(self, buf: str) -> str:
        """Render the auto-complete list as a plain string (line mode / palette)."""
        sugg = autocomplete_suggestions(buf)
        if not sugg:
            return paint("(no matching commands)", C.GRAY)
        return "\n".join(f"  {paint(n, C.CYAN):<20} {paint(d, C.DIM)}" for n, d in sugg[:MAX_SUGGESTIONS])

    def _agents_panel_text(self) -> str:
        return agent_panel(self.registry.all_info() if self.registry else [])

    def _sessions_panel_text(self) -> str:
        rows = [{"id": self.session_id, "title": "current", "status": "active"}]
        return session_panel(rows, active_id=self.session_id)


def _mem_mb() -> float:
    """Best-effort RSS in MB (Linux/Termux)."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    return 0.0
