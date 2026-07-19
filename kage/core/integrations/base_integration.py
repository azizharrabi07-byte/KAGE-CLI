"""core/integrations/base_integration.py — unified integration contract.

Every external service (WhatsApp, Obsidian, Telegram, Discord, ...) subclasses
``BaseIntegration`` to get a consistent lifecycle:

    connect()      — establish the connection (retry/backoff)
    disconnect()   — release resources
    health_check() — probe liveness (retry/backoff + auto-reconnect)
    send(payload)  — push a message/object out
    receive()      — pull pending messages/objects in (no-op if read-only)

All methods return a structured ``ToolResult`` envelope and emit structured
log lines + metrics via ``core.observability``. Resilience (retry / timeout /
exponential backoff / auto-reconnect) is delegated to ``core.health``.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..health import run_with_retry
from ..observability import TraceSpan, add_trace, log_event, record_metric
from ..result import ToolResult

log = logging.getLogger("kage.integration")


class BaseIntegration(ABC):
    """Common base for all integrations."""

    name: str = "base"
    kind: str = "base"

    def __init__(self, *, config: Optional[Dict[str, Any]] = None,
                 retries: int = 3, base_delay: float = 0.1,
                 backoff_factor: float = 2.0, timeout: float = 20.0,
                 auto_reconnect: bool = True) -> None:
        self.config: Dict[str, Any] = config or {}
        self.retries = retries
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.auto_reconnect = auto_reconnect
        self._connected = False

    # -- lifecycle -----------------------------------------------------------
    @abstractmethod
    def connect(self) -> ToolResult:
        """Establish the connection. Returns a ToolResult."""

    def disconnect(self) -> ToolResult:
        was = self._connected
        self._connected = False
        self._log("info", "disconnected", was_connected=was)
        return ToolResult.success({"connected": False})

    @property
    def connected(self) -> bool:
        return self._connected

    def health_check(self) -> ToolResult:
        """Probe liveness with retry + optional auto-reconnect."""
        if not self._connected and self.auto_reconnect:
            res = self.connect()
            if res.ok:
                res.meta["reconnected"] = True
            return res

        def _probe(attempt: int) -> None:
            if not self._alive():
                raise ConnectionError(f"{self.name} not responding")

        result = run_with_retry(_probe, max_attempts=self.retries,
                                base_delay=self.base_delay,
                                backoff_factor=self.backoff_factor,
                                timeout=min(self.timeout, 5.0))
        status = "healthy" if result.ok else "down"
        self._log("info" if result.ok else "warn", f"health {status}",
                  latencyMs=round(result.durationMs, 1), attempts=result.attempts)
        record_metric("tool_call", 1, source=f"integration:{self.name}")
        if not result.ok:
            return ToolResult.failure(result.error or "health check failed",
                                      attempts=result.attempts, durationMs=result.durationMs,
                                      status=status)
        return ToolResult.success({"status": status, "latencyMs": round(result.durationMs, 1)},
                                  attempts=result.attempts, durationMs=result.durationMs)

    def _alive(self) -> bool:
        """Override for a cheap liveness probe. Default: connected flag."""
        return self._connected

    # -- transport -----------------------------------------------------------
    def send(self, payload: Dict[str, Any]) -> ToolResult:
        """Push a message/object out. Subclasses implement ``_send``."""
        return self._guarded("_send", payload)

    def receive(self) -> ToolResult:
        """Pull pending inbound objects. Subclasses implement ``_receive``."""
        return self._guarded("_receive", {})

    # -- internals -----------------------------------------------------------
    def _guarded(self, op: str, payload: Dict[str, Any]) -> ToolResult:
        """Run an op with retry/backoff/auto-reconnect and observability."""
        method = getattr(self, op, None)
        if method is None:
            return ToolResult.failure(f"{self.name} does not implement {op}")

        def _run(attempt: int) -> Any:
            if not self._connected and self.auto_reconnect:
                conn = self.connect()
                if not conn.ok:
                    raise ConnectionError(conn.error or "connect failed")
            return method(payload)

        result = run_with_retry(_run, max_attempts=self.retries,
                                base_delay=self.base_delay,
                                backoff_factor=self.backoff_factor,
                                timeout=self.timeout)
        self._log("info" if result.ok else "warn", f"{op} {result.status}",
                  attempts=result.attempts, durationMs=round(result.durationMs, 1))
        record_metric("tool_call", 1, source=f"integration:{self.name}")
        add_trace(TraceSpan(agent=self.name, action=op, decision=result.status,
                            durationMs=round(result.durationMs, 1)))
        return result

    def _send(self, payload: Dict[str, Any]) -> Any:  # pragma: no cover - override
        raise NotImplementedError

    def _receive(self, payload: Dict[str, Any]) -> Any:  # pragma: no cover - override
        raise NotImplementedError

    # -- logging -------------------------------------------------------------
    def _log(self, level: str, message: str, **meta: Any) -> None:
        log_event(level, f"integration:{self.name}", message, **meta)
        if level == "info":
            log.info("%s %s %s", self.name, message, meta)
        else:
            log.warning("%s %s %s", self.name, message, meta)
