"""core/tool_manager.py — central tool access layer (KAGE v2).

Agents NEVER call tools directly. They ask the ToolManager, which owns a set of
named tools (filesystem, git, terminal, browser, memory, docker, search, ...).
This lets tools be swapped, mocked or permission-gated without touching every
agent. Each call returns the structured ``ToolResult`` envelope.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .result import ToolResult
from .security import sanitize_path, validate_shell

log = logging.getLogger("kage.tools")


@dataclass
class ToolSpec:
    name: str
    description: str
    run: Callable[..., ToolResult]
    permissions: List[str]


class ToolManager:
    """Registers, gates and dispatches named tools."""

    def __init__(self, *, root: str = "", allow_destructive: bool = False) -> None:
        self.root = Path(root or ".").resolve()
        self.allow_destructive = allow_destructive
        self._tools: Dict[str, ToolSpec] = {}
        self._install_builtins()

    # -- registration --------------------------------------------------------
    def register(self, name: str, run: Callable[..., ToolResult],
                 description: str = "", permissions: Optional[List[str]] = None) -> None:
        self._tools[name] = ToolSpec(name, description, run, permissions or [])

    def list(self) -> List[str]:
        return sorted(self._tools)

    def describe(self) -> List[Dict[str, Any]]:
        return [{"name": t.name, "description": t.description,
                 "permissions": list(t.permissions)} for t in self._tools.values()]

    # -- dispatch ------------------------------------------------------------
    def call(self, name: str, **kwargs: Any) -> ToolResult:
        spec = self._tools.get(name)
        if spec is None:
            return ToolResult.failure(f"unknown tool: {name}")
        try:
            return spec.run(**kwargs)
        except Exception as exc:  # noqa: BLE001
            log.warning("tool %s failed: %s", name, exc)
            return ToolResult.failure(str(exc))

    # -- builtin tools -------------------------------------------------------
    def _install_builtins(self) -> None:
        self.register("filesystem.read", self._fs_read,
                      "Read a file from the workspace root.")
        self.register("filesystem.write", self._fs_write,
                      "Write/overwrite a workspace file.")
        self.register("filesystem.list", self._fs_list,
                      "List workspace files.")
        self.register("terminal.run", self._terminal,
                      "Run a validated shell command in the workspace.")
        self.register("git.exec", self._git,
                      "Run a git subcommand in the workspace.")
        self.register("memory.recall", self._noop_tool,
                      "Recall from shared memory (wired by orchestrator).")
        self.register("browser.fetch", self._noop_tool,
                      "Fetch a URL (wired to a browser tool).")
        self.register("search.web", self._noop_tool,
                      "Web search (wired to a search provider).")

    def _fs_read(self, path: str) -> ToolResult:
        try:
            target = (self.root / sanitize_path(path)).resolve()
            return ToolResult.success({"path": str(target), "content": target.read_text()})
        except (OSError, ValueError) as exc:
            return ToolResult.failure(str(exc))

    def _fs_write(self, path: str, content: str) -> ToolResult:
        try:
            target = (self.root / sanitize_path(path)).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            return ToolResult.success({"path": str(target), "bytes": len(content)})
        except (OSError, ValueError) as exc:
            return ToolResult.failure(str(exc))

    def _fs_list(self, path: str = ".") -> ToolResult:
        try:
            target = (self.root / sanitize_path(path)).resolve()
            entries = sorted(p.name for p in target.iterdir())
            return ToolResult.success({"path": str(target), "entries": entries})
        except (OSError, ValueError) as exc:
            return ToolResult.failure(str(exc))

    def _terminal(self, command: str, timeout: float = 30.0) -> ToolResult:
        try:
            validate_shell(command)  # raises on unsafe commands
        except ValueError as exc:
            return ToolResult.failure(str(exc))
        try:
            proc = subprocess.run(command, shell=True, capture_output=True,
                                  text=True, timeout=timeout, cwd=str(self.root))  # noqa: S602
            return ToolResult.success({"exit_code": proc.returncode,
                                       "stdout": proc.stdout[-8000:],
                                       "stderr": proc.stderr[-2000:]})
        except subprocess.TimeoutExpired:
            return ToolResult.failure("timeout")
        except OSError as exc:
            return ToolResult.failure(str(exc))

    def _git(self, args: str) -> ToolResult:
        try:
            parts = ["git", "-C", str(self.root)] + args.split()
            proc = subprocess.run(parts, capture_output=True, text=True,
                                  timeout=30, check=False)
            ok = proc.returncode == 0
            return ToolResult(ok and {"stdout": proc.stdout} or None,
                              error=None if ok else proc.stderr.strip(),
                              status="ok" if ok else "error")
        except (OSError, subprocess.SubprocessError) as exc:
            return ToolResult.failure(str(exc))

    @staticmethod
    def _noop_tool(**_: Any) -> ToolResult:
        return ToolResult.success({"note": "tool not wired in this build"})
