"""agents/bridge/base.py — base class for all external-system bridges.

KAGE builds bridges, not clones. A bridge translates a request to the external
system's contract, invokes it, and translates the response back. It NEVER
duplicates reasoning the integrated system already provides. Each bridge is a
thin adapter over a subprocess/HTTP/IPC boundary.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Any, Dict, Optional

from ...core.base_agent import BaseAgent
from ...core.result import ToolResult

log = logging.getLogger("kage.bridge")


class BridgeAgent(BaseAgent):
    """Base for bridges to external systems (OpenCode, OpenClaw, ...)."""

    #: the external command/binary used to invoke the system
    binary: str = ""
    #: how to reach it if not a CLI (e.g. an HTTP endpoint)
    endpoint: str = ""

    def wake(self) -> None:
        self._awake = True
        self._available = self._detect()

    def _detect(self) -> bool:
        """Return True if the external system is reachable."""
        return bool(self.binary) and shutil.which(self.binary) is not None

    @property
    def available(self) -> bool:
        return getattr(self, "_available", False)

    def sleep(self) -> None:
        self._awake = False

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if not self.available:
            return self._unavailable_result()
        result = self.translate_and_call(task)
        return result.to_dict()

    # -- to be overridden ----------------------------------------------------
    def translate_and_call(self, task: Dict[str, Any]) -> ToolResult:  # pragma: no cover
        raise NotImplementedError

    def _unavailable_result(self) -> Dict[str, Any]:
        return {"status": "error", "data": None,
                "error": f"{self.name}: external system '{self.binary or self.endpoint}' not available"}

    # -- low level -----------------------------------------------------------
    def _run_cli(self, args: list, *, cwd: str = "", timeout: float = 60.0,
                 stdin: Optional[str] = None) -> ToolResult:
        try:
            proc = subprocess.run([self.binary, *args], capture_output=True, text=True,
                                  timeout=timeout, cwd=cwd or None, input=stdin, check=False)
            if proc.returncode == 0:
                return ToolResult.success({"stdout": proc.stdout, "stderr": proc.stderr})
            return ToolResult.failure(f"{self.binary} exit {proc.returncode}: {proc.stderr.strip()}")
        except subprocess.TimeoutExpired:
            return ToolResult.failure(f"{self.binary} timeout")
        except OSError as exc:
            return ToolResult.failure(str(exc))
