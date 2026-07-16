#!/usr/bin/env python3
"""
scheduler.py — Cron-like scheduler for Kage agents.
Uses simple sleep-loop (no external cron needed on Termux).
"""

import json
import sys
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable


def _parse_cron(expr: str) -> Dict:
    """Parse cron expression like '0 9 * * *' into a dict."""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: '{expr}'. Expected 5 space-separated parts.")
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "weekday": parts[4],
    }


def _cron_matches(cron: Dict, dt: datetime) -> bool:
    """Check if a datetime matches a cron expression."""
    def match_field(field: str, value: int) -> bool:
        if field == "*":
            return True
        if "/" in field:
            _, step = field.split("/")
            return value % int(step) == 0
        if "-" in field:
            start, end = field.split("-")
            return int(start) <= value <= int(end)
        if "," in field:
            return value in [int(x) for x in field.split(",")]
        return int(field) == value

    try:
        return (
            match_field(cron["minute"], dt.minute)
            and match_field(cron["hour"], dt.hour)
            and match_field(cron["day"], dt.day)
            and match_field(cron["month"], dt.month)
            and match_field(cron["weekday"], dt.weekday())
        )
    except (ValueError, TypeError, ZeroDivisionError):
        return False


class Scheduler:
    """Runs scheduled tasks in a background thread."""

    def __init__(self, wake_fn: Callable):
        """wake_fn: function(agent_name, task_data) to wake an agent."""
        self.wake_fn = wake_fn
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.jobs: List[Dict] = []
        self._last_runs: Dict[int, str] = {}  # job_id -> "YYYY-MM-DD HH:MM"

    def add_job(self, job_id: int, cron: str, agent: str, task: Dict):
        """Add a scheduled job."""
        self.remove_job(job_id)
        self.jobs.append({
            "id": job_id,
            "cron": _parse_cron(cron),
            "cron_raw": cron,
            "agent": agent,
            "task": task,
        })

    def remove_job(self, job_id: int):
        """Remove a scheduled job."""
        self.jobs = [j for j in self.jobs if j["id"] != job_id]
        if job_id in self._last_runs:
            del self._last_runs[job_id]

    def _loop(self):
        """Main scheduler loop — checks every 15 seconds."""
        while self.running:
            now = datetime.now()
            minute_key = now.strftime("%Y-%m-%d %H:%M")

            for job in list(self.jobs):
                try:
                    job_id = job["id"]
                    # Skip if already executed in this exact minute
                    if self._last_runs.get(job_id) == minute_key:
                        continue

                    if _cron_matches(job["cron"], now):
                        self._last_runs[job_id] = minute_key
                        # Execute in separate thread to not block scheduler
                        threading.Thread(
                            target=self._run_job,
                            args=(job["agent"], job["task"]),
                            daemon=True
                        ).start()
                except Exception as e:
                    print(f"[SCHEDULER] Error in job {job.get('id')}: {e}", file=sys.stderr)

            time.sleep(15)

    def _run_job(self, agent: str, task: Dict):
        try:
            self.wake_fn(agent, task)
        except Exception as e:
            print(f"[SCHEDULER] Error executing job task for agent '{agent}': {e}", file=sys.stderr)

    def start(self):
        """Start the scheduler in a background thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def get_jobs(self) -> List[Dict]:
        """Get all scheduled jobs."""
        return [
            {"id": j["id"], "cron": j["cron_raw"], "agent": j["agent"], "task": j["task"]}
            for j in self.jobs
        ]
