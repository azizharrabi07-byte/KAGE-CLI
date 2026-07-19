"""agents/bridge/opencode.py — OpenCode bridge.

Delegates software-engineering tasks (code generation, refactoring, repo
editing, test generation) to OpenCode. KAGE never reimplements OpenCode's
internal capabilities — it just hands the task over and returns the result.
"""

from __future__ import annotations

from typing import Any, Dict

from ...core.result import ToolResult
from .base import BridgeAgent


class OpenCodeBridgeAgent(BridgeAgent):
    name = "opencode-bridge"
    kind = "bridge"
    description = "Bridges software-engineering tasks to OpenCode."
    emoji = "💻"
    binary = "opencode"

    def translate_and_call(self, task: Dict[str, Any]) -> ToolResult:
        goal = str(task.get("goal", task.get("task", "")))
        repo = str(task.get("repo", task.get("cwd", "")))
        # Translate to OpenCode's CLI contract. Flags are illustrative; adjust
        # to the installed OpenCode version's actual surface.
        args = ["--non-interactive", "--prompt", goal]
        if repo:
            args += ["--cwd", repo]
        res = self._run_cli(args, cwd=repo or None)
        if res.ok:
            res.meta["summary"] = f"OpenCode handled: {goal[:80]}"
        return res
