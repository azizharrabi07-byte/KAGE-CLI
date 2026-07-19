"""agents/system/agent.py — device health monitoring (Sentinel).

Reports battery, storage, CPU/load and memory. On Termux it prefers
``termux-api`` helpers; on plain Linux it parses ``/proc`` and ``os.statvfs``
so it works without psutil (which often fails to build on Termux).
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from typing import Any, Dict, Optional

from ...core.base_agent import BaseAgent


class SystemAgent(BaseAgent):
    name = "system"
    kind = "system"
    description = "Reports host/device health: battery, storage, CPU, memory."
    emoji = "🛡️"

    def wake(self) -> None:
        self._awake = True
        self._host = platform.node() or "device"

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        op = str(task.get("op", task.get("action", "health")))
        if op in ("health", "system.health", "status"):
            return {"status": "ok", "data": self.report(), "error": None}
        if op in ("battery", "system.battery"):
            return {"status": "ok", "data": self.battery(), "error": None}
        if op in ("storage", "system.storage"):
            return {"status": "ok", "data": self.storage(task.get("path")), "error": None}
        if op in ("cpu", "load", "system.cpu"):
            return {"status": "ok", "data": self.cpu(), "error": None}
        if op in ("memory", "mem", "system.memory"):
            return {"status": "ok", "data": self.memory(), "error": None}
        return {"status": "error", "data": None, "error": f"unknown system op: {op}"}

    def report(self) -> Dict[str, Any]:
        return {"host": self._host, "battery": self.battery(),
                "storage": self.storage(), "cpu": self.cpu(), "memory": self.memory()}

    def battery(self) -> Dict[str, Any]:
        out = self._run(["termux-battery-status"])
        if out:
            try:
                data = json.loads(out)
                return {"percent": data.get("percentage"), "status": data.get("status", "").lower(), "source": "termux-api"}
            except json.JSONDecodeError:
                pass
        cap = self._read_int("/sys/class/power_supply/battery/capacity")
        status = self._read_str("/sys/class/power_supply/battery/status")
        if cap is not None:
            return {"percent": cap, "status": status.lower(), "source": "sysfs"}
        return {"percent": None, "status": "unknown", "source": "unavailable"}

    def storage(self, path: Optional[str] = None) -> Dict[str, Any]:
        target = os.path.expanduser(path or "~")
        try:
            st = os.statvfs(target)
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            used = total - (st.f_bfree * st.f_frsize)
            return {"path": target, "total": total, "used": used, "free": free,
                    "percent_free": round(free / total * 100, 1) if total else 0.0, "source": "statvfs"}
        except OSError as exc:
            return {"error": str(exc), "source": "unavailable"}

    def cpu(self) -> Dict[str, Any]:
        loadavg = self._read_floats("/proc/loadavg", count=3)
        cores = os.cpu_count() or 1
        return {"loadavg": loadavg if loadavg else [0.0, 0.0, 0.0], "cores": cores,
                "percent": round((loadavg[0] / cores) * 100, 1) if loadavg and cores else 0.0,
                "source": "/proc/loadavg"}

    def memory(self) -> Dict[str, Any]:
        info = self._read_keyvals("/proc/meminfo")
        total = info.get("MemTotal", 0)
        avail = info.get("MemAvailable", 0)
        return {"total_kb": total, "available_kb": avail, "used_kb": total - avail,
                "percent_used": round((total - avail) / total * 100, 1) if total else 0.0,
                "source": "/proc/meminfo"}

    @staticmethod
    def _run(cmd: list, timeout: float = 3.0) -> Optional[str]:
        if shutil.which(cmd[0]) is None:
            return None
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
            return proc.stdout if proc.returncode == 0 else None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    @staticmethod
    def _read_str(path: str) -> str:
        try:
            with open(path) as f:
                return f.read().strip()
        except OSError:
            return ""

    @staticmethod
    def _read_int(path: str) -> Optional[int]:
        s = SystemAgent._read_str(path)
        try:
            return int(s)
        except ValueError:
            return None

    @staticmethod
    def _read_floats(path: str, *, count: int = 3):
        s = SystemAgent._read_str(path)
        if not s:
            return None
        try:
            return [float(x) for x in s.split()[:count]]
        except ValueError:
            return None

    @staticmethod
    def _read_keyvals(path: str) -> Dict[str, int]:
        out: Dict[str, int] = {}
        try:
            with open(path) as f:
                for line in f:
                    if ":" in line:
                        key, _, val = line.partition(":")
                        digits = "".join(ch for ch in val if ch.isdigit())
                        if digits:
                            out[key.strip()] = int(digits)
        except OSError:
            pass
        return out

    def sleep(self) -> None:
        self._awake = False
