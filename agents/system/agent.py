#!/usr/bin/env python3
"""
System Agent — Battery, storage, CPU via termux-api and Linux standard interfaces.
"""

import gc
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False

    def wake(self, task_data: dict) -> dict:
        """Wake up and execute."""
        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        """Check phone health and return structured JSON."""
        result = {}

        # Battery
        result["battery"] = self._get_battery()

        # Storage
        result["storage"] = self._get_storage()

        # CPU
        result["cpu"] = self._get_cpu()

        # Uptime
        result["uptime"] = self._get_uptime()

        return {"status": "done", "output": result}

    def _get_battery(self) -> dict:
        try:
            out = subprocess.run(
                ["termux-battery-status"], capture_output=True, text=True, timeout=5
            )
            if out.returncode == 0 and out.stdout.strip():
                return json.loads(out.stdout)
        except Exception:
            pass

        # Fallback to sysfs (standard Linux/Android)
        try:
            capacity_file = Path("/sys/class/power_supply/battery/capacity")
            status_file = Path("/sys/class/power_supply/battery/status")
            if capacity_file.exists():
                percentage = int(capacity_file.read_text().strip())
                status = status_file.read_text().strip() if status_file.exists() else "UNKNOWN"
                return {"percentage": percentage, "status": status, "source": "sysfs"}
        except Exception:
            pass

        return {"status": "termux-api not installed", "percentage": 100}

    def _get_storage(self) -> dict:
        for path in ["/data", "/sdcard", "/"]:
            try:
                out = subprocess.run(
                    ["df", "-h", path], capture_output=True, text=True, timeout=5
                )
                if out.returncode == 0:
                    lines = out.stdout.strip().split("\n")
                    if len(lines) >= 2:
                        parts = lines[1].split()
                        if len(parts) >= 5:
                            return {
                                "mount": path,
                                "total": parts[1],
                                "used": parts[2],
                                "available": parts[3],
                                "use_percent": parts[4],
                            }
            except Exception:
                continue
        return {"error": "Could not query storage information"}

    def _get_cpu(self) -> dict:
        try:
            out = subprocess.run(
                ["top", "-n", "1", "-b"], capture_output=True, text=True, timeout=5
            )
            if out.returncode == 0:
                lines = out.stdout.strip().split("\n")
                cpu_line = next((l for l in lines if "cpu" in l.lower()), "")
                if cpu_line:
                    return {"raw": cpu_line[:200]}
        except Exception:
            pass

        try:
            with open("/proc/loadavg", "r") as f:
                loadavg = f.read().strip()
                return {"load_average": loadavg}
        except Exception as e:
            return {"error": str(e)}

    def _get_uptime(self) -> str:
        try:
            with open("/proc/uptime", "r") as f:
                uptime_secs = float(f.read().split()[0])
                hours = int(uptime_secs // 3600)
                minutes = int((uptime_secs % 3600) // 60)
                return f"{hours}h {minutes}m"
        except Exception:
            return "unknown"

    def sleep(self):
        self.alive = False
        gc.collect()
