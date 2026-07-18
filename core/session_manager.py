"""
core/session_manager.py
SQLite-based session and conversation history management.
"""

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

KAGE_DIR = Path.home() / ".kage"
DB_PATH = KAGE_DIR / "sessions.db"


def init_db() -> None:
    KAGE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            action_type TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """)
    conn.commit()
    conn.close()


def ensure_db() -> None:
    if not DB_PATH.exists():
        init_db()


def create_session(title: Optional[str] = None) -> str:
    ensure_db()
    session_id = f"sess_{int(time.time())}_{hash(title or '') % 10000}"
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET is_active = 0")
    cursor.execute(
        "INSERT INTO sessions (session_id, title, is_active) VALUES (?, ?, 1)",
        (session_id, title or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
    )
    conn.commit()
    conn.close()
    return session_id


def get_active_session() -> Optional[str]:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT session_id FROM sessions WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def list_sessions(limit: int = 10) -> List[Dict]:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, COUNT(m.id) as message_count
        FROM sessions s
        LEFT JOIN messages m ON s.session_id = m.session_id
        GROUP BY s.session_id
        ORDER BY s.updated_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    sessions = [dict(row) for row in rows]
    conn.close()
    return sessions


def resume_session(session_id: str) -> bool:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
    if not cursor.fetchone():
        conn.close()
        return False
    cursor.execute("UPDATE sessions SET is_active = 0")
    cursor.execute(
        "UPDATE sessions SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()
    return True


def delete_session(session_id: str) -> bool:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
    return True


def add_message(session_id: str, role: str, content: str, action_type: Optional[str] = None) -> None:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, action_type) VALUES (?, ?, ?, ?)",
        (session_id, role, content, action_type),
    )
    cursor.execute(
        "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()


def get_session_messages(session_id: str, limit: int = 50) -> List[Dict]:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
        (session_id, limit),
    )
    rows = cursor.fetchall()
    messages = [dict(row) for row in rows]
    conn.close()
    return messages


def get_session_context(session_id: str, max_messages: int = 10) -> str:
    messages = get_session_messages(session_id, limit=max_messages)
    if not messages:
        return ""
    lines = ["# Recent Conversation History"]
    for msg in messages:
        role = msg["role"].upper()
        content = msg["content"][:500]
        lines.append(f"[{role}]: {content}")
    return "\n".join(lines)


def get_session_summary(session_id: str) -> str:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    session = cursor.fetchone()
    if not session:
        conn.close()
        return "Session not found."
    cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,))
    msg_count = cursor.fetchone()[0]
    conn.close()
    session_dict = dict(session)
    return (
        f"Session: {session_dict['session_id']}\n"
        f"Title: {session_dict['title']}\n"
        f"Created: {session_dict['created_at']}\n"
        f"Messages: {msg_count}\n"
        f"Active: {'Yes' if session_dict['is_active'] else 'No'}"
    )


def handle_session_command(sub_action: str, arg: Optional[str] = None) -> str:
    if sub_action == "new":
        session_id = create_session(arg)
        return f"✅ New session started: `{session_id}`"
    elif sub_action == "resume":
        if not arg:
            return "❌ Usage: /resume <session_id>"
        if resume_session(arg):
            return f"✅ Resumed session: `{arg}`"
        return f"❌ Session not found: `{arg}`"
    elif sub_action == "list":
        sessions = list_sessions()
        if not sessions:
            return "No sessions found."
        lines = ["📋 Sessions:"]
        for s in sessions:
            active = "🟢" if s["is_active"] else "⚪"
            lines.append(f"{active} `{s['session_id']}` — {s['title']} ({s['message_count']} msgs)")
        return "\n".join(lines)
    elif sub_action == "delete":
        if not arg:
            return "❌ Usage: /delete <session_id>"
        delete_session(arg)
        return f"🗑️ Deleted session: `{arg}`"
    elif sub_action == "info":
        if not arg:
            active = get_active_session()
            if not active:
                return "No active session."
            arg = active
        return get_session_summary(arg)
    else:
        return f"❌ Unknown session command: `{sub_action}`. Use: /new, /resume, /list, /delete, /info"


if __name__ == "__main__":
    init_db()
    sid = create_session("Test Session")
    print(f"Created: {sid}")
    add_message(sid, "user", "Hello!")
    add_message(sid, "assistant", "Hi there!")
    print(get_session_context(sid))
    print(handle_session_command("list"))
