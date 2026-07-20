"""cli/tui.py — OpenCode-style terminal REPL for KAGE.

Features:
  • Beautiful ASCII banner + persistent status line
  • Tab     → agent list panel (with running/idle status)
  • Ctrl+P  → command palette (all slash commands)
  • Ctrl+F  → session list (pin active session)
  • Ctrl+L  → clear screen   Ctrl+C/Ctrl+D → quit
  • Colour-coded output (green/yellow/red) — auto-disabled when piped
  • Full CLI ↔ Discord parity via the unified command registry

Input uses raw terminal mode (termios/tty) on POSIX/Termux for key capture, and
degrades gracefully to plain line input when stdin is not a TTY (CI/pipe/test).
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from .. import __version__
from . import commands as cmdmod
from .theme import (C, agent_panel, banner, clear_screen, color_enabled,
                    command_palette, paint, session_panel, status_color, status_line)

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
            os.environ.get("LLM_PROVIDER", "groq").lower(), os.environ.get("LLM_PROVIDER", "Groq"))
        model = os.environ.get("LLM_MODEL", "llama-3.3-70b")
        n_agents = len(self.registry.list()) if self.registry else 0
        return status_line(version=__version__, provider=providers, model=model,
                           agents=n_agents, session=self.session_id, memory_mb=_mem_mb())

    def show_agents(self) -> None:
        agents = self.registry.all_info() if self.registry else []
        self.print(agent_panel(agents))

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
        """Process one input line. Returns text to display, or None to quit."""
        line = line.strip()
        if not line:
            return None
        if line in ("/exit", "/quit"):
            return "__quit__"
        # unified slash commands first
        out = cmdmod.run_slash(line, self.ctx())
        if out is not None:
            return out
        # fall through to the supervisor
        if self.supervisor is None:
            return paint("(no supervisor connected)", C.YELLOW)
        msg = line[1:] if line.startswith("/") else line
        self.history.append(msg)
        resp = self.supervisor.think(msg, user_id=self.ctx()["default_user"])
        head = paint(f"{getattr(resp, 'agent', 'Kage')} · {resp.intent}", status_color("ok" if resp.ok else "error"), bold=True)
        return f"{head}\n{resp.text}"

    # -- main loop -----------------------------------------------------------
    def run(self) -> int:
        clear_screen()
        self.print(self.render_banner())
        self.print()
        interactive = sys.stdin.isatty() and sys.stdout.isatty()
        if interactive:
            return self._loop_raw()
        return self._loop_line()

    def _loop_line(self) -> int:
        """Line-based fallback (pipes, tests, non-TTY)."""
        self.print(paint('KAGE REPL (line mode) — type /help, /exit to quit', C.DIM))
        while True:
            try:
                line = input(paint("kage❯ ", C.MAGENTA, bold=True))
            except (EOFError, KeyboardInterrupt):
                self.print()
                return 0
            out = self.handle_line(line)
            if out == "__quit__":
                self.print(paint("bye 👋", C.CYAN))
                return 0
            if out is not None:
                self.print(out)

    def _loop_raw(self) -> int:  # pragma: no cover - needs a real TTY
        """Raw key-capture loop with Tab/Ctrl+P/Ctrl+F handling."""
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        buf = ""
        try:
            tty.setraw(fd)
            self._draw_prompt(buf)
            while True:
                ch = sys.stdin.read(1)
                if ch in (KEY_CTRL_C, KEY_CTRL_D):
                    self._write_line(paint("bye 👋", C.CYAN))
                    return 0
                if ch == KEY_CTRL_L:
                    clear_screen(); self._draw_prompt(buf); continue
                if ch == KEY_TAB:
                    self._show_panel(self._agents_panel_text()); self._draw_prompt(buf); continue
                if ch == KEY_CTRL_P:
                    self._show_panel(command_palette(cmdmod.palette())); self._draw_prompt(buf); continue
                if ch == KEY_CTRL_F:
                    self._show_panel(self._sessions_panel_text()); self._draw_prompt(buf); continue
                if ch in (KEY_ENTER, KEY_NL):
                    self._write_line("")
                    out = self.handle_line(buf)
                    if out == "__quit__":
                        self._write_line(paint("bye 👋", C.CYAN)); return 0
                    if out is not None:
                        self._write_line(out)
                    buf = ""
                    self._draw_prompt(buf)
                    continue
                if ch == KEY_ESC:
                    buf = ""; self._draw_prompt(buf); continue
                if ch == "\x7f":  # backspace
                    buf = buf[:-1]; self._draw_prompt(buf); continue
                if ch.isprintable():
                    buf += ch; self._draw_prompt(buf)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def _draw_prompt(self, buf: str) -> None:  # pragma: no cover
        prompt = paint("kage❯ ", C.MAGENTA, bold=True)
        self.stream.write("\r\033[K" + prompt + buf)
        self.stream.flush()

    def _write_line(self, text: str) -> None:  # pragma: no cover
        self.stream.write("\r\033[K" + text + "\n")
        self.stream.flush()

    def _show_panel(self, text: str) -> None:  # pragma: no cover
        self.stream.write("\r\033[K" + text + "\n")
        self.stream.flush()

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
