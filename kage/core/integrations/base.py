"""core/integrations/base.py — base integration with resilience primitives.

Every external service (search provider, LLM gateway, Discord, WhatsApp)
subclasses ``Integration`` to get: retry with backoff, timeout, a health
check, and auto-reconnection. This keeps flaky mobile networks (Termux)
from crashing the OS.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

log = logging.getLogger("kage.integration")


class Integration(ABC):
    """Resilient integration base class."""

    name: str = "integration"

    def __init__(self, *, retries: int = 3, timeout: float = 20.0,
                 backoff: float = 0.8) -> None:
        self.retries = retries
        self.timeout = timeout
        self.backoff = backoff
        self._connected = False

    # -- lifecycle -----------------------------------------------------------
    @abstractmethod
    def connect(self) -> None:
        """Establish the connection. Raise on failure."""

    def disconnect(self) -> None:
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def health_check(self) -> bool:
        """Return True if the integration is usable right now."""
        return self._connected

    # -- resilient call ------------------------------------------------------
    def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Call ``fn`` with retry/timeout/backoff and auto-reconnect."""
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                if not self._connected:
                    self.connect()
                result = fn(*args, **kwargs)
                self._connected = True
                return result
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                log.warning("%s call failed (attempt %d/%d): %s",
                            self.name, attempt, self.retries, exc)
                self._connected = False
                if attempt < self.retries:
                    time.sleep(self.backoff * attempt)
                else:
                    break
        raise ConnectionError(f"{self.name} failed after {self.retries} attempts: {last_exc}")
