"""core/cache.py — tiny disk cache with TTL for search/research results.

Keeps Termux resource usage low by avoiding repeated network work.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional


class DiskCache:
    def __init__(self, root: str = ".kage/cache", default_ttl: int = 3600) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

    def _key(self, namespace: str, key: str) -> Path:
        digest = hashlib.sha256(key.encode()).hexdigest()[:24]
        return self.root / f"{namespace}_{digest}.json"

    def get(self, namespace: str, key: str) -> Optional[Any]:
        p = self._key(namespace, key)
        if not p.exists():
            return None
        try:
            blob = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        if time.time() - blob.get("ts", 0) > blob.get("ttl", self.default_ttl):
            p.unlink(missing_ok=True)
            return None
        return blob.get("value")

    def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        p = self._key(namespace, key)
        p.write_text(json.dumps({"ts": time.time(), "ttl": ttl or self.default_ttl, "value": value}))

    def clear(self, namespace: Optional[str] = None) -> int:
        removed = 0
        for f in self.root.glob("*.json"):
            if namespace is None or f.name.startswith(namespace):
                f.unlink(missing_ok=True)
                removed += 1
        return removed
