"""core/session.py — SQLite-backed conversation sessions.

One session per (transport, user). The supervisor can start/resume/list/end
sessions so context can be scoped (e.g. a Discord thread vs a DM).
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import List, Optional


class SessionStore:
    def __init__(self, db_path: str = ".kage/kage.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                role TEXT NOT NULL,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            """
        )
        self.conn.commit()

    # -- sessions ------------------------------------------------------------
    def create(self, user_id: str, platform: str = "cli", title: str = "New session") -> int:
        now = time.time()
        cur = self.conn.execute(
            "INSERT INTO sessions(user_id, platform, title, status, created_at, updated_at) "
            "VALUES(?,?,?,?,?,?)",
            (user_id, platform, title, "active", now, now),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list(self, user_id: str) -> List[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM sessions WHERE user_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()

    def active(self, user_id: str) -> Optional[int]:
        row = self.conn.execute(
            "SELECT id FROM sessions WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return int(row["id"]) if row else None

    def resume(self, session_id: int) -> bool:
        cur = self.conn.execute(
            "UPDATE sessions SET status='active', updated_at=? WHERE id=?",
            (time.time(), session_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def end(self, session_id: int) -> bool:
        cur = self.conn.execute("UPDATE sessions SET status='ended' WHERE id=?", (session_id,))
        self.conn.commit()
        return cur.rowcount > 0

    # -- messages ------------------------------------------------------------
    def add_message(self, session_id: int, role: str, author: str, content: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO messages(session_id, role, author, content, created_at) VALUES(?,?,?,?,?)",
            (session_id, role, author, content, time.time()),
        )
        self.conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (time.time(), session_id))
        self.conn.commit()
        return int(cur.lastrowid)

    def history(self, session_id: int, limit: int = 50) -> List[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, limit)
        ).fetchall()[::-1]

    def close(self) -> None:
        self.conn.close()
