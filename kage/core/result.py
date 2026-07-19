"""core/result.py — the universal structured envelope (Phase 4).

Every tool and integration returns a consistent result with status, data and
error, plus durationMs/attempts for observability. This mirrors the
``ToolResult`` contract used across the KAGE OS control plane.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """Structured result envelope returned by all tools/integrations."""

    status: str  # "ok" | "error"
    data: Optional[Any] = None
    error: Optional[str] = None
    durationMs: float = 0.0
    attempts: int = 1
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def success(cls, data: Any = None, *, attempts: int = 1,
                durationMs: float = 0.0, **meta: Any) -> "ToolResult":
        return cls(status="ok", data=data, error=None,
                   attempts=attempts, durationMs=durationMs, meta=dict(meta))

    @classmethod
    def failure(cls, error: str, *, data: Any = None, attempts: int = 1,
                durationMs: float = 0.0, **meta: Any) -> "ToolResult":
        return cls(status="error", data=data, error=error,
                   attempts=attempts, durationMs=durationMs, meta=dict(meta))


class timed:
    """Context manager that measures elapsed milliseconds."""

    def __init__(self) -> None:
        self.ms: float = 0.0

    def __enter__(self) -> "timed":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.ms = (time.perf_counter() - self._t0) * 1000.0
