#!/usr/bin/env python3
"""
OpenHands Agent — Sandboxed Workspace Execution & Software Control Agent for KAGE OS.
Inspired by https://github.com/OpenHands/OpenHands
Actions: execute_cmd, run_python, write_code, status
"""

import gc
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False
        self.workspace_dir = Path(__file__).parent.parent.parent

    def wake(self, task_data: dict) -> dict:
        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        action = task_data.get("action", "status")
        command = task_data.get("command", task_data.get("cmd", ""))
        code = task_data.get("code", "")
        filepath = task_data.get("path", task_data.get("filepath", ""))
        content = task_data.get("content", "")

        try:
            if action in ("execute_cmd", "run_cmd", "cmd"):
                if not command:
                    return {"status": "error", "output": "Missing 'command' parameter"}
                
                approved = self.context.permissions.require_approval(
                    "openhands.execute_cmd",
                    f"Execute workspace command: {command[:80]}"
                )
                if not approved:
                    return {"status": "denied", "output": "Command execution denied by user"}

                return self._run_command(command)

            elif action in ("run_python", "eval_python"):
                if not code:
                    return {"status": "error", "output": "Missing 'code' parameter"}

                approved = self.context.permissions.require_approval(
                    "openhands.run_python",
                    f"Execute Python script:\n{code[:100]}..."
                )
                if not approved:
                    return {"status": "denied", "output": "Python execution denied by user"}

                return self._run_python_code(code)

            elif action == "write_code":
                if not filepath or not content:
                    return {"status": "error", "output": "Missing 'path' or 'content' parameter"}

                approved = self.context.permissions.require_approval(
                    "openhands.write_code",
                    f"Write file to workspace: {filepath}"
                )
                if not approved:
                    return {"status": "denied", "output": "File write denied by user"}

                return self._write_workspace_file(filepath, content)

            elif action == "status":
                return {
                    "status": "done",
                    "output": {"workspace": str(self.workspace_dir), "agent": "OpenHands Sandbox"}
                }

            else:
                return {"status": "error", "output": f"Unknown action: {action}"}

        except Exception as e:
            return {"status": "error", "output": str(e)}

    def _run_command(self, cmd: str) -> Dict:
        """Run shell command in workspace."""
        res = subprocess.run(
            cmd,
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

    def _run_python_code(self, code: str) -> Dict:
        """Run inline Python code snippet using python executable."""
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

    def _write_workspace_file(self, filepath: str, content: str) -> Dict:
        """Write file into workspace path safely."""
        target_path = (self.workspace_dir / filepath).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return {"status": "written", "file": str(target_path)}

    def sleep(self):
        self.alive = False
        gc.collect()
