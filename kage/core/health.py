"""core/health.py — retry / timeout / backoff + integration health (Phase 4).

A generic ``run_with_retry`` with exponential backoff and an optional per-call
timeout, plus a small ``probe`` helper for one-shot health checks with an
auto-reconnect attempt. Used by every integration (Discord, Telegram, WhatsApp,
Obsidian, LLM providers).
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from .result import ToolResult, timed


class HealthTimeout(Exception):
    """Raised when a call exceeds its timeout window."""


def call_with_timeout(fn: Callable, timeout: Optional[float], *args: Any, **kwargs: Any) -> Any:
    """Run ``fn`` in a worker thread; raise HealthTimeout past ``timeout`` seconds."""
    if not timeout:
        return fn(*args, **kwargs)
    box: dict = {}

    def _runner() -> None:
        try:
            box["value"] = fn(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - re-raised by the caller
            box["error"] = exc

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise HealthTimeout(f"timeout after {timeout}s")
    if "error" in box:
        raise box["error"]
    return box.get("value")


def run_with_retry(fn: Callable[[int], Any], *, max_attempts: int = 3,
                   base_delay: float = 0.1, backoff_factor: float = 2.0,
                   timeout: Optional[float] = None) -> ToolResult:
    """Run ``fn(attempt)`` with exponential backoff.

    ``fn`` receives the 1-based attempt number so a caller can simulate
    transient failures. Returns a structured ``ToolResult``.
    """
    last_error: Optional[str] = None
    with timed() as t:
        for attempt in range(1, max_attempts + 1):
            try:
                value = call_with_timeout(fn, timeout, attempt)
                return ToolResult.success(value, attempts=attempt, durationMs=t.ms)
            except BaseException as exc:  # noqa: BLE001 - retry anything, report last
                last_error = str(exc)
                if attempt < max_attempts:
                    time.sleep(min(base_delay * (backoff_factor ** (attempt - 1)), 8.0))
    return ToolResult.failure(last_error or "unknown error",
                              attempts=max_attempts, durationMs=t.ms)


def probe(check: Callable[[], ToolResult], *, auto_reconnect: bool = True) -> ToolResult:
    """Health-check helper: one attempt, plus an optional reconnect attempt."""
    result = check()
    if not result.ok and auto_reconnect:
        second = check()
        if second.ok:
            second.meta["reconnected"] = True
            return second
    return result
