"""
core/long_memory.py
SQLite-based long-term memory for facts.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict

KAGE_DIR = Path.home() / ".kage"
DB_PATH = KAGE_DIR / "long_memory.db"


def init_db() -> None:
    KAGE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT DEFAULT 'general',
            fact TEXT NOT NULL,
            source TEXT,
            confidence REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def ensure_db() -> None:
    if not DB_PATH.exists():
        init_db()


def add_fact(fact: str, category: str = "general", source: str = "", confidence: float = 1.0) -> int:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO facts (category, fact, source, confidence) VALUES (?, ?, ?, ?)",
        (category, fact, source, confidence),
    )
    fact_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return fact_id


def search_facts(query: str, limit: int = 5) -> List[Dict]:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM facts WHERE fact LIKE ? ORDER BY updated_at DESC LIMIT ?",
        (f"%{query}%", limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_facts(limit: int = 50) -> List[Dict]:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM facts ORDER BY updated_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_fact(fact_id: int, new_fact: str) -> bool:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE facts SET fact = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_fact, fact_id),
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_fact(fact_id: int) -> bool:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
