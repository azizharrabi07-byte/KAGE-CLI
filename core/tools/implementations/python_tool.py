#!/usr/bin/env python3
"""
python_tool.py — Inline Python Evaluation Tool.
Part of Phase 8 Tool Framework.
"""

import sys
import subprocess
from typing import Dict, Any
from core.tools.base import BaseTool, ToolMetadata, PermissionLevel
from core.tools.registry import ToolRegistry


class PythonTool(BaseTool):
    """Evaluates Python code snippet in sub-process."""

    def __init__(self):
        super().__init__(ToolMetadata(
            name="python_eval",
            description="Evaluates inline Python code in isolated subprocess",
            category="execution",
            permission_level=PermissionLevel.SENSITIVE,
            parameters_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python source code string"}
                },
                "required": ["code"]
            },
            timeout_seconds=30.0
        ))

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        code = args["code"]
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=self.metadata.timeout_seconds,
        )
        return {
            "exit_code": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
        }


ToolRegistry.register(PythonTool())
