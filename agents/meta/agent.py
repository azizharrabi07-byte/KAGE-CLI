#!/usr/bin/env python3
"""
Meta Agent — Self-upgrade via git pull.
Runs tests, asks permission, applies updates.
"""

import gc
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False
        self.kage_dir = Path(__file__).parent.parent.parent

    def wake(self, task_data: dict) -> dict:
        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        action = task_data.get("action", "check")

        if action == "pull":
            return self._do_pull()
        elif action == "check":
            return self._check_status()
        elif action == "restart":
            return self._restart()
        else:
            return {"status": "error", "output": f"Unknown action: {action}"}

    def _check_status(self) -> dict:
        """Check if there are updates available."""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.kage_dir), "status", "--porcelain"],
                capture_output=True, text=True, timeout=10
            )
            has_changes = bool(result.stdout.strip())

            # Check remote
            fetch = subprocess.run(
                ["git", "-C", str(self.kage_dir), "fetch", "origin"],
                capture_output=True, text=True, timeout=10
            )
            status = subprocess.run(
                ["git", "-C", str(self.kage_dir), "status", "-sb"],
                capture_output=True, text=True, timeout=10
            )
            behind = "behind" in status.stdout

            return {
                "status": "done",
                "output": {
                    "has_local_changes": has_changes,
                    "has_updates": behind,
                    "status": status.stdout.strip()[:200],
                },
            }
        except Exception as e:
            return {"status": "error", "output": str(e)}

    def _do_pull(self) -> dict:
        """Pull latest changes. Requires permission."""
        try:
            # Ask permission
            approved = self.context.permissions.require_approval(
                "meta.upgrade",
                "Upgrade KAGE to latest version from git?"
            )
            if not approved:
                return {"status": "denied", "output": "Upgrade denied by user"}

            # Stash local changes
            subprocess.run(
                ["git", "-C", str(self.kage_dir), "stash"],
                capture_output=True, text=True, timeout=10
            )

            # Pull
            result = subprocess.run(
                ["git", "-C", str(self.kage_dir), "pull", "origin", "main"],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                return {"status": "error", "output": f"git pull failed: {result.stderr}"}

            # Run tests if available
            tests_dir = self.kage_dir / "tests"
            if tests_dir.exists():
                test_result = subprocess.run(
                    [sys.executable, "-m", "pytest", str(tests_dir), "-q"],
                    capture_output=True, text=True, timeout=60
                )
                if test_result.returncode != 0:
                    return {
                        "status": "error",
                        "output": f"Tests failed after upgrade:\n{test_result.stdout}\n{test_result.stderr}"
                    }

            return {
                "status": "done",
                "output": {
                    "pulled": True,
                    "message": result.stdout.strip()[:200],
                    "tests_passed": True,
                },
            }
        except Exception as e:
            return {"status": "error", "output": str(e)}

    def _restart(self) -> dict:
        """Restart the kage supervisor."""
        try:
            # Touch the lock file to signal restart
            lock_file = self.kage_dir / ".kage.lock"
            if lock_file.exists():
                lock_file.unlink()
            return {"status": "done", "output": "Restart signal sent"}
        except Exception as e:
            return {"status": "error", "output": str(e)}

    def sleep(self):
        self.alive = False
        gc.collect()
