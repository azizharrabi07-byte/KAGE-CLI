#!/usr/bin/env python3
"""
store.py — Persistent Multi-Table Memory Storage Engine for KAGE OS.
Stores memory items across types in SQLite kage.db memory_store table.
Part of Phase 7 Memory Engine Upgrade.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from .base import MemoryItem, MemoryType

DB_PATH = Path(__file__).parent.parent.parent / "kage.db"


class MemoryStore:
    """SQLite-backed multi-type persistent memory store."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_table()

    def _get_conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_table(self):
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL DEFAULT 5.0,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    metadata_json TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def save_item(self, item: MemoryItem) -> int:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO memory_items (memory_type, user_id, content, importance, created_at, expires_at, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.memory_type.value,
                    item.user_id,
                    item.content,
                    item.importance,
                    item.created_at,
                    item.expires_at,
                    json.dumps(item.metadata, default=str),
                )
            )
            item.item_id = cursor.lastrowid
            conn.commit()
            return item.item_id
        finally:
            conn.close()

    def get_user_items(self, user_id: str, memory_type: Optional[MemoryType] = None) -> List[MemoryItem]:
        conn = self._get_conn()
        try:
            if memory_type:
                rows = conn.execute(
                    "SELECT * FROM memory_items WHERE user_id = ? AND memory_type = ? ORDER BY id DESC",
                    (user_id, memory_type.value)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memory_items WHERE user_id = ? ORDER BY id DESC",
                    (user_id,)
                ).fetchall()

            items = []
            for r in rows:
                meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                item = MemoryItem(
                    memory_type=MemoryType(r["memory_type"]),
                    content=r["content"],
                    user_id=r["user_id"],
                    importance=r["importance"],
                    created_at=r["created_at"],
                    expires_at=r["expires_at"],
                    item_id=r["id"],
                    metadata=meta,
                )
                if not item.is_expired():
                    items.append(item)

            return items
        finally:
            conn.close()

    def delete_item(self, item_id: int) -> bool:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM memory_items WHERE id = ?", (item_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    def cleanup_expired(self) -> int:
        now_str = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM memory_items WHERE expires_at IS NOT NULL AND expires_at < ?", (now_str,))
            count = cursor.rowcount
            conn.commit()
            return count
        finally:
            conn.close()
