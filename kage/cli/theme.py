"""cli/theme.py — ANSI colors, ASCII banner & status-line rendering.

Pure rendering helpers (return strings) so they are fully unit-testable without
a real terminal. The TUI (cli/tui.py) composes these for the OpenCode-style
interface.

Colour policy (clean, professional):
  • prompt / accent → cyan        • text → white
  • success → green               • warning → yellow
  • error → red                   • banner / chrome → white / grey
Colors auto-disable when stdout is not a TTY or NO_COLOR is set.
"""

from __future__ import annotations

import os
import re
import shutil
from typing import Iterable

# --- ANSI -------------------------------------------------------------------

class C:
    """ANSI escape sequences."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"   # kept for compatibility; not used in the default theme
    CYAN = "\033[36m"
    GRAY = "\033[90m"
    WHITE = "\033[97m"     # bright white for body text


_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


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


def visible_len(text: str) -> int:
    """Length of ``text`` ignoring ANSI escapes (public, used by the TUI)."""
    return len(_ANSI_RE.sub("", text))


def status_color(status: str) -> str:
    """Map a status word to its colour: green/yellow/red/grey."""
    s = (status or "").lower()
    if s in ("ok", "healthy", "awake", "completed", "running", "success", "on"):
        return C.GREEN
    if s in ("executing", "degraded", "paused", "draft", "warn", "warning"):
        return C.YELLOW
    if s in ("error", "down", "failed"):
        return C.RED
    if s in ("sleeping", "off", "needs_confirmation"):
        return C.GRAY
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
    """Render the welcome banner (white/grey chrome) as a compact string."""
    on = color_enabled() if enabled is None else enabled
    width = 61
    top = paint("┌" + "─" * width + "┐", C.GRAY, enabled=on)
    bot = paint("└" + "─" * width + "┘", C.GRAY, enabled=on)
    border = paint("│", C.GRAY, enabled=on)
    lines = [top]
    for art_line in BANNER_ART.splitlines():
        art = paint(art_line, C.WHITE, bold=True, enabled=on)
        pad = (width - len(art_line)) // 2
        lines.append(border + " " * pad + art + " " * (width - pad - len(art_line)) + border)
    title = paint("KAGE AI OS", C.WHITE, bold=True, enabled=on)
    ver = paint(f"v{version}", C.CYAN, enabled=on) if version else ""
    lines.append(_row(f"{title} {ver}".strip(), width, on))
    lines.append(_row(paint(subtitle, C.DIM, enabled=on), width, on))
    lines.append(_row(paint('Ask anything... "What can you do?"', C.GRAY, enabled=on), width, on))
    keys = (f"{paint('Tab', C.CYAN, enabled=on)} agents   "
            f"{paint('Ctrl+P', C.CYAN, enabled=on)} commands   "
            f"{paint('Ctrl+F', C.CYAN, enabled=on)} sessions")
    lines.append(_row(keys, width, on))
    lines.append(bot)
    return "\n".join(lines)


def _row(text: str, width: int, on: bool) -> str:
    """A centered banner row inside │ borders."""
    visible = visible_len(text)
    pad = max(2, (width - visible) // 2)
    right = width - visible - pad
    border = paint("│", C.GRAY, enabled=on)
    return border + " " * pad + text + " " * right + border


# --- status line -----------------------------------------------------------

def status_line(*, version: str = "", provider: str = "", model: str = "",
                agents: int = 0, session: str = "", memory_mb: float = 0.0,
                enabled: bool | None = None) -> str:
    """Render the compact persistent status line."""
    on = color_enabled() if enabled is None else enabled
    left_bits = [paint("KAGE", C.WHITE, bold=True, enabled=on) + paint(f" v{version}", C.DIM, enabled=on)]
    pm = _pm(provider, model, on)
    if pm:
        left_bits.append(pm)
    left = " · ".join(left_bits)
    right = "  ".join([f"{paint('Agents:', C.GRAY, enabled=on)} {agents}",
                       f"{paint('Mem:', C.GRAY, enabled=on)} {memory_mb:.0f}MB",
                       f"{paint('Session:', C.GRAY, enabled=on)} {session}"])
    bar = paint("─" * 64, C.GRAY, enabled=on)
    return f"{bar}\n{left}   {right}"


def _pm(provider: str, model: str, on: bool) -> str:
    bits = [b for b in [provider, model] if b]
    return paint(" · ".join(bits), C.CYAN, enabled=on) if bits else ""


# --- panels -----------------------------------------------------------------

def agent_panel(agents: Iterable[dict], *, enabled: bool | None = None) -> str:
    """Render the Tab agent list panel (compact)."""
    on = color_enabled() if enabled is None else enabled
    header = paint("AGENTS", C.WHITE, bold=True, enabled=on)
    rows = []
    for a in agents:
        dot = paint("●", C.GREEN if a.get("awake") else C.GRAY, enabled=on)
        name = paint(f"{a.get('emoji','🤖')} {a.get('name','?'):<12}", C.WHITE, bold=True, enabled=on)
        kind = paint(str(a.get("kind", "")), C.DIM, enabled=on)
        state = paint("running" if a.get("awake") else "idle",
                      status_color("awake" if a.get("awake") else "idle"), enabled=on)
        rows.append(f" {dot} {name} {kind:<12} {state}")
    body = "\n".join(rows) if rows else paint(" (no agents registered)", C.GRAY, enabled=on)
    return f"{header}\n{body}"


def command_palette(commands: Iterable[tuple], *, enabled: bool | None = None) -> str:
    """Render the Ctrl+P command palette (compact). ``commands`` = list of (cmd, desc)."""
    on = color_enabled() if enabled is None else enabled
    header = paint("COMMAND PALETTE", C.WHITE, bold=True, enabled=on)
    rows = []
    for cmd, desc in commands:
        rows.append(f" {paint(cmd, C.CYAN, enabled=on):<22} {paint(desc, C.DIM, enabled=on)}")
    body = "\n".join(rows) if rows else paint(" (no commands)", C.GRAY, enabled=on)
    return f"{header}\n{body}\n {paint('↑↓ select · Enter run · Esc close', C.GRAY, enabled=on)}"


def session_panel(sessions: Iterable[dict], active_id: str | None = None,
                  *, enabled: bool | None = None) -> str:
    """Render the Ctrl+F session list (active one pinned)."""
    on = color_enabled() if enabled is None else enabled
    header = paint("SESSIONS", C.WHITE, bold=True, enabled=on)
    rows = []
    for s in sessions:
        sid = str(s.get("id", "?"))
        marker = paint("📌", C.YELLOW, enabled=on) if sid == str(active_id) else "  "
        title = str(s.get("title", "session"))
        state = paint(str(s.get("status", "")), status_color(s.get("status", "")), enabled=on)
        rows.append(f" {marker} {sid:<10} {title:<24} {state}")
    body = "\n".join(rows) if rows else paint(" (no sessions)", C.GRAY, enabled=on)
    return f"{header}\n{body}"


def clear_screen() -> None:
    if color_enabled():
        print("\033[2J\033[H", end="")


def term_width(default: int = 72) -> int:
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except OSError:
        return default
