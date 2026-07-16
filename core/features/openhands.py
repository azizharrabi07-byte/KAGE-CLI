#!/usr/bin/env python3
"""
OpenHands Sandbox Feature — Sandboxed Shell Execution, Python Evaluation & Code Synthesis.
Available to all agents and brain via context.openhands
Reference: https://github.com/OpenHands/OpenHands
"""

import sys
import subprocess
from pathlib import Path
from typing import Dict, Any


class OpenHandsFeature:
    """Built-in OpenHands Software Execution & Workspace Feature."""

    def __init__(self, context=None):
        self.context = context
        self.workspace_dir = Path(__file__).parent.parent.parent

    def execute_cmd(self, command: str, require_approval: bool = True) -> Dict[str, Any]:
        """Execute bash command in workspace."""
        if require_approval and self.context and hasattr(self.context, "permissions"):
            approved = self.context.permissions.require_approval(
                "openhands.execute_cmd",
                f"Execute command: {command[:80]}"
            )
            if not approved:
                return {"status": "denied", "output": "Command execution denied by user"}

        res = subprocess.run(
            command,
            shell=True,
            cwd=str(self.workspace_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "exit_code": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
        }

    def run_python(self, code: str, require_approval: bool = True) -> Dict[str, Any]:
        """Evaluate inline Python script."""
        if require_approval and self.context and hasattr(self.context, "permissions"):
            approved = self.context.permissions.require_approval(
                "openhands.run_python",
                f"Execute Python code snippet"
            )
            if not approved:
                return {"status": "denied", "output": "Python execution denied by user"}

        res = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(self.workspace_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "exit_code": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
        }

    def write_code(self, path: str, content: str, require_approval: bool = True) -> Dict[str, Any]:
        """Write file to workspace path."""
        if require_approval and self.context and hasattr(self.context, "permissions"):
            approved = self.context.permissions.require_approval(
                "openhands.write_code",
                f"Write file to workspace: {path}"
            )
            if not approved:
                return {"status": "denied", "output": "File writing denied by user"}

        target_path = (self.workspace_dir / path).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return {"status": "written", "file": str(target_path)}
