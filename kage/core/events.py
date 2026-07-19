"""core/events.py — decoupled pub/sub event bus (KAGE v2).

Agents never call each other directly. KAGE publishes events; interested agents
subscribe. This keeps the system modular and lets new agents react to activity
without touching the orchestrator.

Topics are hierarchical strings (e.g. ``task.received``, ``agent.completed``,
``harness.improvement``). Subscriptions may be exact or prefix-wildcard
(``agent.*``). Handlers are plain callables ``handler(event)``; sync handlers run
inline, coroutine handlers can be scheduled by the caller.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List

log = logging.getLogger("kage.events")


@dataclass
class Event:
    topic: str
    payload: Dict[str, Any] = field(default_factory=dict)
    ts: float = 0.0
    source: str = ""

    def __post_init__(self) -> None:
        if not self.ts:
            self.ts = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


Handler = Callable[[Event], None]


class EventBus:
    """In-process event bus with wildcard topic subscriptions."""

    def __init__(self) -> None:
        # exact topic -> handlers, and prefix patterns -> handlers
        self._handlers: Dict[str, List[Handler]] = {}
        self._wild: Dict[str, List[Handler]] = {}
        self._history: List[Event] = []
        self._max_history = 200

    def subscribe(self, topic: str, handler: Handler) -> None:
        if topic.endswith(".*"):
            self._wild.setdefault(topic[:-2], []).append(handler)
        else:
            self._handlers.setdefault(topic, []).append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> bool:
        store = self._handlers.get(topic) or self._wild.get(topic.rstrip(".*"))
        if store and handler in store:
            store.remove(handler)
            return True
        return False

    def publish(self, topic: str, payload: Dict[str, Any] | None = None,
                source: str = "") -> Event:
        event = Event(topic=topic, payload=payload or {}, source=source)
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        delivered = 0
        for h in self._handlers.get(topic, []):
            self._safe(h, event); delivered += 1
        for prefix, hs in self._wild.items():
            if topic.startswith(prefix + ".") or topic == prefix:
                for h in hs:
                    self._safe(h, event); delivered += 1
        log.debug("event %s -> %d handler(s)", topic, delivered)
        return event

    def history(self, topic: str | None = None, limit: int = 50) -> List[Event]:
        rows = self._history
        if topic:
            rows = [e for e in rows if e.topic == topic]
        return list(rows[-limit:])

    @staticmethod
    def _safe(handler: Handler, event: Event) -> None:
        try:
            handler(event)
        except Exception as exc:  # noqa: BLE001 — handlers must never crash the bus
            log.warning("event handler failed for %s: %s", event.topic, exc)


# A process-wide default bus, used by the orchestrator and agents that don't
# need their own isolated bus.
default_bus = EventBus()
