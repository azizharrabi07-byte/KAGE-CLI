"""core/workflows/engine.py — SQLite-backed workflow engine.

A workflow is a list of steps. Each step has: an id, a tool/action, args,
optional ``depends_on`` (predecessors), an optional ``when`` condition, and
``retries``. The engine persists state so long-running research or crew tasks
survive restarts (important on Termux).

Run from the CLI:  ``kage workflow run research.json``
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List


class WorkflowEngine:
    def __init__(self, db_path: str = ".kage/kage.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS workflow_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER NOT NULL REFERENCES workflows(id),
                step_id TEXT NOT NULL,
                action TEXT NOT NULL,
                args TEXT,
                depends_on TEXT,
                cond TEXT,
                retries INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                result TEXT,
                started_at REAL,
                finished_at REAL
            );
            """
        )
        self.conn.commit()

    # -- definition ----------------------------------------------------------
    def load(self, path: str) -> Dict[str, Any]:
        # Strip full-line comments so workflow files stay human-friendly.
        raw = Path(path).read_text()
        cleaned = "\n".join(
            line for line in raw.splitlines()
            if not line.strip().startswith("#")
        )
        spec = json.loads(cleaned)
        wf_id = self.conn.execute(
            "INSERT INTO workflows(name, status, created_at) VALUES(?,?,?)",
            (spec.get("name", Path(path).stem), "pending", time.time()),
        ).lastrowid
        for step in spec.get("steps", []):
            self.conn.execute(
                "INSERT INTO workflow_steps(workflow_id, step_id, action, args, depends_on, "
                "cond, retries) VALUES(?,?,?,?,?,?,?)",
                (
                    wf_id, step["id"], step.get("action", "tool"),
                    json.dumps(step.get("args", {})),
                    json.dumps(step.get("depends_on", [])),
                    step.get("when"), int(step.get("retries", 1)),
                ),
            )
        self.conn.commit()
        return {"workflow_id": wf_id, "steps": len(spec.get("steps", []))}

    # -- execution -----------------------------------------------------------
    def run(self, workflow_id: int, executor) -> Dict[str, Any]:
        """Execute steps in dependency order. ``executor(step) -> dict``."""
        rows = self.conn.execute(
            "SELECT * FROM workflow_steps WHERE workflow_id=?", (workflow_id,)
        ).fetchall()
        results: Dict[str, Any] = {}
        pending: List[sqlite3.Row] = list(rows)
        progress = True
        while pending and progress:
            progress = False
            still: List[sqlite3.Row] = []
            for row in pending:
                deps = json.loads(row["depends_on"] or "[]")
                if not all(results.get(d, {}).get("ok") for d in deps):
                    still.append(row)
                    continue
                cond = row["cond"]
                if cond and not _eval_cond(cond, results):
                    results[row["step_id"]] = {"ok": True, "skipped": True}
                    progress = True
                    continue
                self._set_status(row["id"], "running")
                res = self._exec_with_retry(row, executor)
                results[row["step_id"]] = res
                self._set_status(row["id"], "done" if res.get("ok") else "failed",
                                 json.dumps(res))
                progress = True
            pending = still
        self.conn.execute("UPDATE workflows SET status='done' WHERE id=?", (workflow_id,))
        self.conn.commit()
        return {"workflow_id": workflow_id, "results": results}

    def _exec_with_retry(self, row: sqlite3.Row, executor) -> Dict[str, Any]:
        args = json.loads(row["args"] or "{}")
        for attempt in range(max(1, row["retries"])):
            try:
                self.conn.execute(
                    "UPDATE workflow_steps SET started_at=? WHERE id=?",
                    (time.time(), row["id"]),
                )
                res = executor({"step_id": row["step_id"], "action": row["action"], "args": args})
                if res.get("ok"):
                    self.conn.execute(
                        "UPDATE workflow_steps SET finished_at=? WHERE id=?", (time.time(), row["id"])
                    )
                    return res
            except Exception as exc:  # noqa: BLE001
                res = {"ok": False, "error": str(exc)}
        return res  # type: ignore[name-defined]

    def _set_status(self, row_id: int, status: str, result: str = "") -> None:
        self.conn.execute(
            "UPDATE workflow_steps SET status=?, result=? WHERE id=?", (status, result, row_id)
        )
        self.conn.commit()

    def status(self, workflow_id: int) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT step_id, status, result FROM workflow_steps WHERE workflow_id=?",
            (workflow_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _eval_cond(cond: str, results: Dict[str, Any]) -> bool:
    """Tiny, safe condition evaluator over ``results`` (no eval)."""
    # Supports "step_id.ok" style checks only.
    if "." in cond:
        step, key = cond.split(".", 1)
        return bool(results.get(step, {}).get(key))
    return bool(results.get(cond))
