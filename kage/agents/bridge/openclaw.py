"""agents/bridge/openclaw.py — OpenClaw bridge (computer/GUI control)."""

from __future__ import annotations

from typing import Any, Dict

from ...core.result import ToolResult
from .base import BridgeAgent


class OpenClawBridgeAgent(BridgeAgent):
    name = "openclaw-bridge"
    kind = "bridge"
    description = "Bridges computer-control (mouse/keyboard/GUI) tasks to OpenClaw."
    emoji = "🖱️"
    binary = "openclaw"

    def translate_and_call(self, task: Dict[str, Any]) -> ToolResult:
        goal = str(task.get("goal", ""))
        action = task.get("action", "control")
        res = self._run_cli(["--task", goal, "--mode", str(action)])
        if res.ok:
            res.meta["summary"] = f"OpenClaw performed: {action}"
        return res
