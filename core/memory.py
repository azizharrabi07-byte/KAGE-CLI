#!/usr/bin/env python3
"""
memory.py — SQLite storage for traces, workflows, and state.
All data lives in ~/kage-os/kage.db
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


DB_PATH = Path(__file__).parent.parent / "kage.db"


def _get_conn() -> sqlite3.Connection:
    """Get a connection to the database, creating tables if needed."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            agent TEXT NOT NULL,
            task_json TEXT NOT NULL,
            output_json TEXT,
            error TEXT,
            duration_ms REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            steps_json TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cron TEXT NOT NULL,
            agent TEXT NOT NULL,
            task_json TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            last_run TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def log_trace(agent: str, task: dict, output: dict = None, error: str = None, duration_ms: float = 0) -> int:
    """Log a trace entry. Returns the trace ID."""
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO traces (timestamp, agent, task_json, output_json, error, duration_ms) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), agent, json.dumps(task),
         json.dumps(output) if output else None, error, duration_ms)
    )
    trace_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trace_id


def get_recent_traces(limit: int = 20) -> List[Dict]:
    """Get the last N traces."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM traces ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_trace_by_id(trace_id: int) -> Optional[Dict]:
    """Get a specific trace."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM traces WHERE id = ?", (trace_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Workflow persistence ---

def create_workflow(name: str, steps: list) -> int:
    """Create a workflow. Returns workflow ID."""
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO workflows (name, steps_json, status, created_at) VALUES (?, ?, ?, ?)",
        (name, json.dumps(steps), "pending", datetime.now().isoformat())
    )
    wf_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return wf_id


def update_workflow_status(wf_id: int, status: str):
    """Update workflow status."""
    conn = _get_conn()
    conn.execute("UPDATE workflows SET status = ? WHERE id = ?", (status, wf_id))
    conn.commit()
    conn.close()


def get_workflow(wf_id: int) -> Optional[Dict]:
    """Get a workflow."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM workflows WHERE id = ?", (wf_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_pending_workflows() -> List[Dict]:
    """Get workflows that need to run."""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM workflows WHERE status IN ('pending', 'running')").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Schedule ---

def add_schedule(cron: str, agent: str, task: dict) -> int:
    """Add a scheduled job. Returns job ID."""
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO schedule (cron, agent, task_json, enabled, created_at) VALUES (?, ?, ?, 1, ?)",
        (cron, agent, json.dumps(task), datetime.now().isoformat())
    )
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id


def get_schedules() -> List[Dict]:
    """Get all scheduled jobs."""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM schedule WHERE enabled = 1").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_schedule_run(job_id: int):
    """Mark schedule as last run."""
    conn = _get_conn()
    conn.execute("UPDATE schedule SET last_run = ? WHERE id = ?", (datetime.now().isoformat(), job_id))
    conn.commit()
    conn.close()


def delete_schedule(job_id: int):
    """Delete a scheduled job."""
    conn = _get_conn()
    conn.execute("DELETE FROM schedule WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


# --- Helper ---

def init_db():
    """Initialize the database."""
    _get_conn()
    # Don't print — called from daemon too


if __name__ == "__main__":
    init_db()
