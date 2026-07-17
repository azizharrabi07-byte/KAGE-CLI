#!/usr/bin/env python3
"""
legacy.py — Backward-Compatible SQLite Storage for Traces, Workflows, and Schedules in KAGE OS.
Maintains kage.db operations required by supervisor daemon, workflows, and memory modules.
"""

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

DB_PATH = Path(__file__).parent.parent.parent / "kage.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
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
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO traces (timestamp, agent, task_json, output_json, error, duration_ms) VALUES (?, ?, ?, ?, ?, ?)",
            (
                datetime.now().isoformat(),
                agent,
                json.dumps(task, default=str),
                json.dumps(output, default=str) if output is not None else None,
                error,
                duration_ms
            )
        )
        trace_id = cursor.lastrowid
        conn.commit()
        return trace_id
    finally:
        conn.close()


def get_recent_traces(limit: int = 20) -> List[Dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM traces ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["task"] = json.loads(d["task_json"]) if d.get("task_json") else {}
            except Exception:
                d["task"] = d.get("task_json")
            try:
                d["output"] = json.loads(d["output_json"]) if d.get("output_json") else None
            except Exception:
                d["output"] = d.get("output_json")
            result.append(d)
        return result
    finally:
        conn.close()


def get_trace_by_id(trace_id: int) -> Optional[Dict]:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM traces WHERE id = ?", (trace_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["task"] = json.loads(d["task_json"]) if d.get("task_json") else {}
        except Exception:
            d["task"] = d.get("task_json")
        try:
            d["output"] = json.loads(d["output_json"]) if d.get("output_json") else None
        except Exception:
            d["output"] = d.get("output_json")
        return d
    finally:
        conn.close()


def create_workflow(name: str, steps: list) -> int:
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO workflows (name, steps_json, status, created_at) VALUES (?, ?, ?, ?)",
            (name, json.dumps(steps, default=str), "pending", datetime.now().isoformat())
        )
        wf_id = cursor.lastrowid
        conn.commit()
        return wf_id
    finally:
        conn.close()


def update_workflow_status(wf_id: int, status: str):
    conn = _get_conn()
    try:
        conn.execute("UPDATE workflows SET status = ? WHERE id = ?", (status, wf_id))
        conn.commit()
    finally:
        conn.close()


def get_workflow(wf_id: int) -> Optional[Dict]:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM workflows WHERE id = ?", (wf_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_pending_workflows() -> List[Dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM workflows WHERE status IN ('pending', 'running')").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_schedule(cron: str, agent: str, task: dict) -> int:
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO schedule (cron, agent, task_json, enabled, created_at) VALUES (?, ?, ?, 1, ?)",
            (cron, agent, json.dumps(task, default=str), datetime.now().isoformat())
        )
        job_id = cursor.lastrowid
        conn.commit()
        return job_id
    finally:
        conn.close()


def get_schedules() -> List[Dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM schedule WHERE enabled = 1").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_schedule_run(job_id: int):
    conn = _get_conn()
    try:
        conn.execute("UPDATE schedule SET last_run = ? WHERE id = ?", (datetime.now().isoformat(), job_id))
        conn.commit()
    finally:
        conn.close()


def delete_schedule(job_id: int):
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM schedule WHERE id = ?", (job_id,))
        conn.commit()
    finally:
        conn.close()


def init_db():
    _get_conn().close()
