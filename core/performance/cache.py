#!/usr/bin/env python3
"""
cache.py — Multi-Tier Response & Prompt Cache Engine for KAGE OS.
Supports in-memory and file-backed caching with configurable TTL and automatic expiration.
Part of Phase 10 Performance Optimization.
"""

import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Any, Tuple

CACHE_DIR = Path.home() / ".kage" / "cache"
logger = logging.getLogger("kage.performance.cache")


class ResponseCache:
    """Thread-safe multi-tier cache store for expensive LLM calls, web searches, and tool queries."""

    _memory_cache: Dict[str, Tuple[float, Any]] = {}
    _lock = threading.Lock()

    def __init__(self, default_ttl_seconds: int = 300, cache_dir: Optional[Path] = None):
        self.default_ttl = default_ttl_seconds
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_key(self, key_data: Any) -> str:
        if isinstance(key_data, (dict, list)):
            str_repr = json.dumps(key_data, sort_keys=True, default=str)
        else:
            str_repr = str(key_data)
        return hashlib.sha256(str_repr.encode("utf-8")).hexdigest()

    def get(self, key_data: Any) -> Optional[Any]:
        """Retrieve cached value if present and not expired."""
        key_hash = self._hash_key(key_data)
        now = time.time()

        # 1. Memory Cache lookup
        with self._lock:
            if key_hash in self._memory_cache:
                expires_at, val = self._memory_cache[key_hash]
                if now < expires_at:
                    logger.debug(f"Cache HIT (memory): {key_hash[:8]}")
                    return val
                else:
                    del self._memory_cache[key_hash]

        # 2. Disk Cache lookup
        disk_file = self.cache_dir / f"{key_hash}.json"
        if disk_file.exists():
            try:
                with open(disk_file, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                expires_at = payload.get("expires_at", 0)
                if now < expires_at:
                    val = payload.get("value")
                    # Backfill memory cache
                    with self._lock:
                        self._memory_cache[key_hash] = (expires_at, val)
                    logger.debug(f"Cache HIT (disk): {key_hash[:8]}")
                    return val
                else:
                    disk_file.unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"Cache disk read error: {e}")

        logger.debug(f"Cache MISS: {key_hash[:8]}")
        return None

    def set(self, key_data: Any, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Store value in cache with specified or default TTL."""
        key_hash = self._hash_key(key_data)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = time.time() + ttl

        # Memory update
        with self._lock:
            self._memory_cache[key_hash] = (expires_at, value)

        # Disk update
        disk_file = self.cache_dir / f"{key_hash}.json"
        try:
            payload = {
                "hash": key_hash,
                "created_at": time.time(),
                "expires_at": expires_at,
                "value": value,
            }
            with open(disk_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, default=str)
            return True
        except Exception as e:
            logger.error(f"Cache disk write error: {e}")
            return False

    def clear(self) -> int:
        """Clear all in-memory and disk cache entries."""
        count = 0
        with self._lock:
            count += len(self._memory_cache)
            self._memory_cache.clear()

        for f in self.cache_dir.glob("*.json"):
            try:
                f.unlink()
                count += 1
            except Exception:
                pass
        return count
