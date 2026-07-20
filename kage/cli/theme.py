"""cli/theme.py — ANSI colors, ASCII banner & status-line rendering.

Pure rendering helpers (return strings) so they are fully unit-testable without
a real terminal. The TUI (cli/tui.py) composes these for the OpenCode-style
interface. Colors auto-disable when stdout is not a TTY or NO_COLOR is set.
"""

from __future__ import annotations

import os
import shutil
from typing import Iterable

# --- ANSI -------------------------------------------------------------------

class C:
    """ANSI escape sequences. All empty when color is disabled."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"
    BG_VIOLET = "\033[48;5;54m"


def color_enabled(stream=None) -> bool:
    """True if color should be emitted for the given stream."""
    if os.environ.get("NO_COLOR"):
        return False
    stream = stream or __import__("sys").stdout
    return hasattr(stream, "isatty") and stream.isatty()


def paint(text: str, color: str, *, bold: bool = False, enabled: bool | None = None) -> str:
    """Wrap ``text`` in ANSI color (and optionally bold)."""
    on = color_enabled() if enabled is None else enabled
    if not on or not color:
        return text
    return f"{C.BOLD if bold else ''}{color}{text}{C.RESET}"


def status_color(status: str) -> str:
    """Map a status word to its color."""
    s = (status or "").lower()
    if s in ("ok", "healthy", "awake", "completed", "running", "success", "on"):
        return C.GREEN
    if s in ("executing", "degraded", "paused", "draft", "warn", "warning"):
        return C.YELLOW
    if s in ("error", "down", "failed", "sleeping", "off", "needs_confirmation"):
        return C.RED if s in ("error", "down", "failed") else C.GRAY
    return C.CYAN


# --- ASCII banner -----------------------------------------------------------

BANNER_ART = r"""
  ██╗  ██╗ █████╗  ██████╗ ███████╗
  ██║ ██╔╝██╔══██╗██╔════╝ ██╔════╝
  █████╔╝ ███████║██║  ███╗█████╗
  ██╔═██╗ ██╔══██║██║   ██║██╔══╝
  ██║  ██╗██║  ██║╚██████╔╝███████╗
  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
""".strip("\n")


def banner(version: str = "", subtitle: str = "Terminal AI Operating System",
           *, enabled: bool | None = None) -> str:
    """Render the welcome banner as a string."""
    on = color_enabled() if enabled is None else enabled
    art = "\n".join(paint(line, C.MAGENTA, bold=True, enabled=on) for line in BANNER_ART.splitlines())
    title = paint("KAGE AI OS", C.BOLD, bold=True, enabled=on)
    ver = paint(f"v{version}", C.CYAN, enabled=on) if version else ""
    sub = paint(subtitle, C.DIM, enabled=on)
    hint = paint('Ask anything... "What can you do?"', C.GRAY, enabled=on)
    keys = (f"  {paint('⌘ Tab', C.YELLOW, enabled=on)} agents   "
            f"{paint('⌘ Ctrl+P', C.YELLOW, enabled=on)} commands   "
            f"{paint('⌘ Ctrl+F', C.YELLOW, enabled=on)} sessions")
    width = 61
    top = paint("┌" + "─" * width + "┐", C.GRAY, enabled=on)
    bot = paint("└" + "─" * width + "┘", C.GRAY, enabled=on)
    lines = [top]
    for art_line in BANNER_ART.splitlines():
        pad = (61 - len(art_line)) // 2
        line = paint(art_line, C.MAGENTA, bold=True, enabled=on)
        lines.append(paint("│", C.GRAY, enabled=on) + " " * pad + line + " " * (61 - pad - len(art_line)) + paint("│", C.GRAY, enabled=on))
    lines.append(_row(f"{title} {ver}", width, on))
    lines.append(_row(sub, width, on))
    lines.append(_row(hint, width, on))
    lines.append(_row("", width, on))
    lines.append(_row(keys.strip(), width, on))
    lines.append(bot)
    return "\n".join(lines)


def _row(text: str, width: int, on: bool, *, color: str = "") -> str:
    """A banner row padded inside │ borders."""
    visible = _visible_len(text)
    pad = max(2, (width - visible) // 2)
    right = width - visible - pad
    body = paint(color, "", enabled=on)
    return (paint("│", C.GRAY, enabled=on) + " " * pad + text + " " * right
            + paint("│", C.GRAY, enabled=on))


def _visible_len(text: str) -> int:
    """Length of ``text`` ignoring ANSI escapes (rough)."""
    import re
    return len(re.sub(r"\033\[[0-9;]*m", "", text))


# --- status line -----------------------------------------------------------

def status_line(*, version: str = "", provider: str = "", model: str = "",
                agents: int = 0, session: str = "", memory_mb: float = 0.0,
                enabled: bool | None = None) -> str:
    """Render the persistent bottom status line."""
    on = color_enabled() if enabled is None else enabled
    left = " · ".join(p for p in [paint("KAGE", C.BOLD, bold=True, enabled=on) + paint(f" v{version}", C.DIM, enabled=on),
                                  _pm(provider, model, on)] if p)
    right = "  ".join(p for p in [f"{paint('Agents:', C.GRAY, enabled=on)} {agents}",
                                  f"{paint('Mem:', C.GRAY, enabled=on)} {memory_mb:.0f}MB",
                                  f"{paint('Session:', C.GRAY, enabled=on)} {session}"] if p)
    bar = paint("─" * 64, C.GRAY, enabled=on)
    return f"{bar}\n{left}\n{right}"


def _pm(provider: str, model: str, on: bool) -> str:
    bits = [b for b in [provider, model] if b]
    if not bits:
        return ""
    return paint(" · ".join(bits), C.CYAN, enabled=on)


# --- panels -----------------------------------------------------------------

def agent_panel(agents: Iterable[dict], *, enabled: bool | None = None) -> str:
    """Render the Tab agent list panel."""
    on = color_enabled() if enabled is None else enabled
    header = paint("  AGENTS", C.BOLD, bold=True, enabled=on)
    rows = []
    for a in agents:
        dot = paint("●", C.GREEN if a.get("awake") else C.GRAY, enabled=on)
        name = paint(f"{a.get('emoji','🤖')} {a.get('name','?'):<12}", C.BOLD, enabled=on)
        kind = paint(str(a.get("kind", "")), C.DIM, enabled=on)
        state = paint("running" if a.get("awake") else "idle", status_color("awake" if a.get("awake") else "idle"), enabled=on)
        rows.append(f"  {dot} {name} {kind:<12} {state}")
    body = "\n".join(rows) if rows else paint("  (no agents registered)", C.GRAY, enabled=on)
    return f"{header}\n{body}"


def command_palette(commands: Iterable[tuple], *, enabled: bool | None = None) -> str:
    """Render the Ctrl+P command palette. ``commands`` = list of (cmd, desc)."""
    on = color_enabled() if enabled is None else enabled
    header = paint("  COMMAND PALETTE", C.BOLD, bold=True, enabled=on)
    rows = []
    for cmd, desc in commands:
        rows.append(f"  {paint(cmd, C.CYAN, enabled=on):<22} {paint(desc, C.DIM, enabled=on)}")
    body = "\n".join(rows) if rows else paint("  (no commands)", C.GRAY, enabled=on)
    foot = paint("  ↑↓ select · Enter run · Esc close", C.GRAY, enabled=on)
    return f"{header}\n{body}\n{foot}"


def session_panel(sessions: Iterable[dict], active_id: str | None = None,
                  *, enabled: bool | None = None) -> str:
    """Render the Ctrl+F session list (active one marked/pinned)."""
    on = color_enabled() if enabled is None else enabled
    header = paint("  SESSIONS", C.BOLD, bold=True, enabled=on)
    rows = []
    for s in sessions:
        sid = str(s.get("id", "?"))
        marker = paint("📌", C.YELLOW, enabled=on) if sid == str(active_id) else "  "
        title = str(s.get("title", "session"))
        state = paint(str(s.get("status", "")), status_color(s.get("status", "")), enabled=on)
        rows.append(f"  {marker} {sid:<10} {title:<24} {state}")
    body = "\n".join(rows) if rows else paint("  (no sessions)", C.GRAY, enabled=on)
    return f"{header}\n{body}"


def clear_screen() -> None:
    if color_enabled():
        print("\033[2J\033[H", end="")


def term_width(default: int = 72) -> int:
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except OSError:
        return default
