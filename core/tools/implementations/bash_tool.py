#!/usr/bin/env python3
"""
bash_tool.py — Parameterized Sandboxed Bash Command Tool.
Part of Phase 8 Tool Framework.
"""

import shlex
import subprocess
from typing import Dict, Any
from core.tools.base import BaseTool, ToolMetadata, PermissionLevel
from core.tools.registry import ToolRegistry


class BashTool(BaseTool):
    """Executes bash commands in workspace directory using list-based arguments."""

    def __init__(self, workspace_dir: str = "/home/user/KAGE-CLI"):
        super().__init__(ToolMetadata(
            name="bash_execute",
            description="Executes shell command safely in project workspace",
            category="execution",
            permission_level=PermissionLevel.SENSITIVE,
            parameters_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command string"}
                },
                "required": ["command"]
            },
            timeout_seconds=30.0
        ))
        self.workspace_dir = workspace_dir

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        command_str = args["command"]
        cmd_args = shlex.split(command_str)
        res = subprocess.run(
            cmd_args,
            cwd=self.workspace_dir,
            capture_output=True,
            text=True,
            timeout=self.metadata.timeout_seconds,
        )
        return {
            "exit_code": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
        }


# Auto-register default instance
ToolRegistry.register(BashTool())
