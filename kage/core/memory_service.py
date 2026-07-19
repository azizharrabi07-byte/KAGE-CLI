"""core/memory_service.py — layered shared memory service (KAGE v2).

All agents access memory through ONE interface rather than maintaining isolated
stores. Five layers, scoped from ephemeral to permanent:

    session     — within a single task/session (cleared when it ends)
    project     — per-project facts (rooted at a project path)
    user        — per-user preferences/identity
    knowledge   — reusable, deduplicated facts cache
    longterm    — persistent facts (survives restarts)

Backed by the existing JSON ``MemoryStore`` under the hood so it remains
Termux-friendly and dependency-free.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .memory import MemoryStore

LAYERS = ("session", "project", "user", "knowledge", "longterm")


class MemoryService:
    """Unified layered memory accessed by all agents."""

    def __init__(self, root: str = ".kage/memory") -> None:
        # one MemoryStore per layer; layer is the "user_id" namespace.
        self._store = MemoryStore(root=root)
        self._session: str = "default"
        self._project: Optional[str] = None

    # -- scope setters -------------------------------------------------------
    def set_session(self, session_id: str) -> None:
        self._session = session_id

    def set_project(self, project: Optional[str]) -> None:
        self._project = project

    # -- core API ------------------------------------------------------------
    def remember(self, layer: str, key: str, value: Any) -> None:
        self._check(layer)
        self._store.set(self._ns(layer), key, str(value))

    def recall(self, layer: str, key: str) -> Optional[str]:
        self._check(layer)
        return self._store.get(self._ns(layer)).get(key)

    def forget(self, layer: str, key: str) -> bool:
        self._check(layer)
        return self._store.forget(self._ns(layer), key)

    def layer_keys(self, layer: str) -> Dict[str, str]:
        self._check(layer)
        return self._store.get(self._ns(layer))

    def clear_session(self) -> int:
        store = self._store.get(self._ns("session"))
        n = len(store)
        for k in list(store):
            self._store.forget(self._ns("session"), k)
        return n

    def search(self, query: str, layers: Optional[List[str]] = None) -> Dict[str, Dict[str, str]]:
        """Substring search across layers. Returns {layer: {key: value}}."""
        q = (query or "").lower()
        out: Dict[str, Dict[str, str]] = {}
        for layer in (layers or LAYERS):
            hits = {k: v for k, v in self._store.get(self._ns(layer)).items()
                    if q in k.lower() or q in v.lower()}
            if hits:
                out[layer] = hits
        return out

    def snapshot(self) -> Dict[str, Dict[str, str]]:
        return {layer: self._store.get(self._ns(layer)) for layer in LAYERS}

    # -- internals -----------------------------------------------------------
    def _ns(self, layer: str) -> str:
        if layer == "session":
            return f"session:{self._session}"
        if layer == "project":
            return f"project:{self._project or 'default'}"
        return layer  # user / knowledge / longterm are global namespaces

    @staticmethod
    def _check(layer: str) -> None:
        if layer not in LAYERS:
            raise ValueError(f"unknown memory layer '{layer}'; choose from {LAYERS}")
