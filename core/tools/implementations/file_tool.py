#!/usr/bin/env python3
"""
file_tool.py — Safe Workspace File Operations Tool.
Part of Phase 8 Tool Framework.
"""

from pathlib import Path
from typing import Dict, Any
from core.tools.base import BaseTool, ToolMetadata, PermissionLevel
from core.tools.registry import ToolRegistry


class FileTool(BaseTool):
    """Reads and writes workspace files safely."""

    def __init__(self, root_dir: str = "/home/user/KAGE-CLI"):
        super().__init__(ToolMetadata(
            name="file_ops",
            description="Reads, writes, or checks files within allowed workspace root",
            category="filesystem",
            permission_level=PermissionLevel.SENSITIVE,
            parameters_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "read | write | exists"},
                    "path": {"type": "string", "description": "Relative file path"},
                    "content": {"type": "string", "description": "Text content to write"}
                },
                "required": ["action", "path"]
            }
        ))
        self.root_dir = Path(root_dir).resolve()

    def run(self, args: Dict[str, Any]) -> Any:
        action = args["action"]
        target_path = (self.root_dir / args["path"]).resolve()

        # Path Traversal Prevention
        if not str(target_path).startswith(str(self.root_dir)):
            raise PermissionError(f"Access denied: path '{args['path']}' leaves authorized workspace root")

        if action == "read":
            if not target_path.exists():
                raise FileNotFoundError(f"File '{args['path']}' does not exist")
            return target_path.read_text(encoding="utf-8")

        elif action == "write":
            content = args.get("content", "")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            return f"Successfully written file to '{target_path.relative_to(self.root_dir)}'"

        elif action == "exists":
            return target_path.exists()

        else:
            raise ValueError(f"Unknown action '{action}'")


ToolRegistry.register(FileTool())
