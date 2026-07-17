#!/usr/bin/env python3
"""
System Agent — Battery, storage, CPU via termux-api.
"""

import gc
import json
import os
import sys
import subprocess
from typing import Dict


class Agent:
    def __init__(self, context):
        self.context = context  # has brain, memory, permissions
        self.alive = False

    def wake(self, task_data: dict) -> dict:
        """Wake up and execute. Heavy imports happen here."""
        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        """Check phone health and return structured JSON."""
        result = {}

        # Battery
        try:
            out = subprocess.run(
                ["termux-battery-status"], capture_output=True, text=True, timeout=5
            )
            if out.returncode == 0:
                result["battery"] = json.loads(out.stdout)
            else:
                result["battery"] = {"error": out.stderr.strip()}
        except FileNotFoundError:
            result["battery"] = {"status": "termux-api not installed", "percentage": 100}
        except Exception as e:
            result["battery"] = {"error": str(e)}

        # Storage
        try:
            out = subprocess.run(
                ["df", "-h", "/data"], capture_output=True, text=True, timeout=5
            )
            if out.returncode == 0:
                lines = out.stdout.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[1].split()
                    result["storage"] = {
                        "total": parts[1],
                        "used": parts[2],
                        "available": parts[3],
                        "use_percent": parts[4],
                    }
            else:
                result["storage"] = {"error": out.stderr.strip()}
        except Exception as e:
            result["storage"] = {"error": str(e)}

        # CPU
        try:
            out = subprocess.run(
                ["top", "-n", "1", "-b"], capture_output=True, text=True, timeout=5
            )
            if out.returncode == 0:
                # Parse first few lines for CPU usage
                lines = out.stdout.strip().split("\n")
                cpu_line = next((l for l in lines if "Cpu" in l or "cpu" in l.lower()), "")
                result["cpu"] = {"raw": cpu_line[:200]}
        except Exception as e:
            result["cpu"] = {"error": str(e)}

        # Uptime
        try:
            with open("/proc/uptime") as f:
                uptime_secs = float(f.read().split()[0])
                hours = int(uptime_secs // 3600)
                minutes = int((uptime_secs % 3600) // 60)
                result["uptime"] = f"{hours}h {minutes}m"
        except Exception:
            result["uptime"] = "unknown"

        return {"status": "done", "output": result}

    def sleep(self):
        """Clean up — no resources to release."""
        self.alive = False
        gc.collect()
