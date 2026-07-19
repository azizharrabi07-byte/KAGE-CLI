"""core/observability.py — structured logging, metrics and traces (Phase 6).

- JSON log lines written to ``~/.kage/logs/kage.log`` (secrets scrubbed).
- Lightweight in-memory counters/timers for metrics.
- A ring buffer of trace spans capturing the agent decision chain for debugging.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Deque, Dict, List

from .secrets import scrub

_LOG_DIR = Path(os.path.expanduser("~/.kage/logs"))
_METRICS: Dict[str, Dict[str, float]] = {}
_TRACES: Deque[Dict[str, Any]] = deque(maxlen=500)
_logger_ready = False


def _logger() -> logging.Logger:
    global _logger_ready
    logger = logging.getLogger("kage.obs")
    if not _logger_ready:
        try:
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(_LOG_DIR / "kage.log")
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        except OSError:
            pass
        _logger_ready = True
    return logger


def log_event(level: str, source: str, message: str, **meta: Any) -> Dict[str, Any]:
    """Emit one scrubbed JSON log line and return the record."""
    record = {"ts": time.time(), "level": level, "source": source,
              "message": message, "meta": meta or {}}
    _logger().info(scrub(json.dumps(record, default=str)))
    return record


def record_metric(kind: str, value: float = 1.0, *, source: str = "", unit: str = "count") -> None:
    bucket = _METRICS.setdefault(kind, {"total": 0.0, "count": 0.0})
    bucket["total"] += value
    bucket["count"] += 1


def metric_summary() -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for kind, b in _METRICS.items():
        avg = b["total"] / b["count"] if b["count"] else 0.0
        out[kind] = {"total": b["total"], "count": b["count"], "avg": avg}
    return out


@dataclass
class TraceSpan:
    agent: str
    action: str
    decision: str = ""
    input: Any = None
    output: Any = None
    durationMs: float = 0.0


def add_trace(span: TraceSpan) -> None:
    d = asdict(span)
    d["ts"] = time.time()
    _TRACES.append(d)


def recent_traces(limit: int = 50) -> List[Dict[str, Any]]:
    return list(_TRACES)[-limit:]


def reset() -> None:
    """Clear in-memory metrics and traces (used by tests)."""
    _METRICS.clear()
    _TRACES.clear()
