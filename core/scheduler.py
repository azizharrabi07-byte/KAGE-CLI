#!/usr/bin/env python3
"""
scheduler.py — Cron-like scheduler for Kage agents.
Uses simple sleep-loop (no external cron needed on Termux).
"""

import json
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
        raise ValueError(f"Invalid cron expression: {expr}")
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

    return (
        match_field(cron["minute"], dt.minute)
        and match_field(cron["hour"], dt.hour)
        and match_field(cron["day"], dt.day)
        and match_field(cron["month"], dt.month)
        and match_field(cron["weekday"], dt.weekday())
    )


class Scheduler:
    """Runs scheduled tasks in a background thread."""

    def __init__(self, wake_fn: Callable):
        """wake_fn: function(agent_name, task_data) to wake an agent."""
        self.wake_fn = wake_fn
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.jobs: List[Dict] = []
        self.last_check = datetime.now()

    def add_job(self, job_id: int, cron: str, agent: str, task: Dict):
        """Add a scheduled job."""
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

    def _loop(self):
        """Main scheduler loop — checks every 30 seconds."""
        while self.running:
            now = datetime.now()
            for job in self.jobs:
                try:
                    if _cron_matches(job["cron"], now):
                        # Don't re-run within the same minute
                        if self.last_check.minute == now.minute:
                            continue
                        self.wake_fn(job["agent"], job["task"])
                except Exception as e:
                    print(f"[SCHEDULER] Error in job {job['id']}: {e}", file=sys.stderr)

            self.last_check = now
            time.sleep(30)

    def start(self):
        """Start the scheduler in a background thread."""
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
