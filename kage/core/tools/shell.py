"""core/tools/shell.py — sandboxed shell execution tool.

Destructive by default: requires permission. Commands are validated
(core.security.validate_shell) and only safe, allow-listed forms run without
explicit ``allow_destructive``.
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict

from ..security import validate_shell
from .base import Tool, ToolMeta, ToolSchema


class ShellTool(Tool):
    meta = ToolMeta(
        name="shell.run",
        description="Run a validated shell command. Destructive; needs permission.",
        schema=ToolSchema(required=["command"], optional={"timeout": "int"}),
        destructive=True,
        permissions=["shell"],
    )

    def run(self, args: Dict[str, Any], user_id: str = "cli") -> Dict[str, Any]:
        command = validate_shell(str(args["command"]))  # raises ValueError if unsafe
        timeout = int(args.get("timeout", 15))
        try:
            proc = subprocess.run(  # noqa: S602
                command, shell=True, capture_output=True, text=True, timeout=timeout,
            )
            return {
                "ok": proc.returncode == 0,
                "command": command,
                "exit_code": proc.returncode,
                "stdout": proc.stdout[:8000],
                "stderr": proc.stderr[:2000],
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "command": command, "error": "timeout"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "command": command, "error": str(exc)}
