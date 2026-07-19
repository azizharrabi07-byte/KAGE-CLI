"""core/actions.py — turn the supervisor's thoughts into actions (Phase: alive).

The supervisor is *proactive*: when an LLM (or a rule-based fallback) emits an
action, this module parses it and executes it. Supported actions:

    {"action": "shell", "command": "ls -la ~/kage-os"}
    {"action": "file_write", "path": "README.md",
     "mode": "append|overwrite|create", "content": "Kage is alive"}
    {"action": "create_agent", "name": "weather",
     "description": "Reports weather", "emoji": "🌧️"}
    {"action": "reply", "text": "plain text"}

Safety is tiered (the OS acts freely, but the worst patterns are gated):
  * FORBIDDEN  — never executed (fork bombs, wiping root devices).
  * DANGEROUS  — destructive; runs only when ``allow_all`` (else needs confirm).
  * everything else (ls, mkdir, git add/commit/push, file edits, scaffolding)
    runs immediately, which is the "decisive" golden rule.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .security import restrict_to_sandbox

# --- LLM instruction --------------------------------------------------------

ACTION_SCHEMA = (
    "You are Kage, a proactive AI OS supervisor. When the user asks for a "
    "concrete action, reply with EXACTLY ONE fenced JSON action block and "
    "nothing else. Supported actions:\n"
    '  {"action": "shell", "command": "ls -la ~/kage-os"}\n'
    '  {"action": "file_write", "path": "README.md", "mode": "append", '
    '"content": "Kage is alive"}  # mode: create|overwrite|append\n'
    '  {"action": "create_agent", "name": "weather", "description": "...", '
    '"emoji": "🌧️"}\n'
    '  {"action": "reply", "text": "any plain explanation"}\n'
    "Rules: paths are relative to the project root. Emit only the JSON block "
    "inside a ```json fence. If no action is needed, use a reply action."
)

# --- safety tiers -----------------------------------------------------------

# Never allowed, period.
FORBIDDEN = [
    re.compile(r":\s*\(\s*\)\s*\{.*\}.*;.*:", re.DOTALL),   # fork bomb
    re.compile(r"\bdd\b[^|]*\bof=/dev/(sd|nvme|hd|disk)"),
    re.compile(r"\bmkfs\b"),
    re.compile(r">\s*/dev/(sd|nvme|hd|disk)"),
]

# Destructive — require explicit allow_all (confirm in interactive mode).
DANGEROUS = [
    re.compile(r"\brm\s+-rf?\s+/(?:\s|$|\*)"),
    re.compile(r"\brm\s+-rf?\s+~(?:\s|$)"),
    re.compile(r"\brm\s+-rf?\s+\*\s*$"),
    re.compile(r"\bchmod\s+-R\s+777\s+/"),
    re.compile(r"\bshutdown\b|\breboot\b|\bhalt\b|\bpoweroff\b", re.IGNORECASE),
    re.compile(r"\bgit\s+push\b.*(--force|-f\b)"),
    re.compile(r"\bsudo\b", re.IGNORECASE),
]


def _matches(patterns: List[re.Pattern], text: str) -> bool:
    return any(p.search(text) for p in patterns)


# --- action model -----------------------------------------------------------

@dataclass
class Action:
    kind: str
    params: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""


def parse_actions(text: str) -> Tuple[List[Action], str]:
    """Extract JSON action blocks from ``text``.

    Returns (actions, display_text) where display_text has the action blocks
    removed (so transports don't echo raw JSON).
    """
    candidates: List[str] = []

    # 1) fenced code blocks (```json ... ``` or ``` ... ```)
    for m in re.finditer(r"```[a-zA-Z]*\n?(.*?)```", text, re.DOTALL):
        candidates.append(m.group(1).strip())

    working = re.sub(r"```[a-zA-Z]*\n?.*?```", "", text, flags=re.DOTALL)

    # 2) bare JSON objects via incremental decode (handles nested braces)
    for i in (m.start() for m in re.finditer(r"\{", working)):
        try:
            obj, end = json.JSONDecoder().raw_decode(working[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "action" in obj:
            candidates.append(working[i:i + end])

    actions: List[Action] = []
    consumed: List[str] = []
    for c in candidates:
        try:
            data = json.loads(c)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and "action" in item:
                actions.append(Action(str(item["action"]), dict(item), c))
                consumed.append(c)

    display = text
    for c in consumed:
        display = display.replace(c, "")
    display = re.sub(r"```[a-zA-Z]*\n?.*?```", "", display, flags=re.DOTALL)
    return actions, display.strip()


# --- executor --------------------------------------------------------------

class ActionExecutor:
    """Executes parsed actions with tiered safety."""

    def __init__(self, *, root: str = "", allow_all: bool = False,
                 timeout: float = 30.0) -> None:
        self.root = (Path(root or os.environ.get("KAGE_ROOT") or os.getcwd())).resolve()
        self.allow_all = allow_all or os.environ.get(
            "KAGE_ALLOW_DESTRUCTIVE", "").lower() in ("1", "true", "yes")
        self.timeout = timeout

    # -- dispatch ------------------------------------------------------------
    def execute(self, action: Action) -> Dict[str, Any]:
        kind = (action.kind or "").strip().lower()
        if kind == "shell":
            return self._shell(action.params)
        if kind in ("file_write", "file.edit", "edit", "write"):
            return self._file_write(action.params)
        if kind in ("create_agent", "agent.create"):
            return self._create_agent(action.params)
        if kind == "reply":
            return {"ok": True, "kind": "reply", "text": str(action.params.get("text", ""))}
        return {"ok": False, "kind": kind, "error": f"unknown action: {kind}"}

    # -- shell ---------------------------------------------------------------
    def _shell(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cmd = str(params.get("command", "")).strip()
        if not cmd:
            return {"ok": False, "kind": "shell", "error": "empty command"}
        if _matches(FORBIDDEN, cmd):
            return {"ok": False, "kind": "shell", "status": "forbidden",
                    "command": cmd, "error": "command blocked by safety policy"}
        if _matches(DANGEROUS, cmd) and not self.allow_all:
            return {"ok": False, "kind": "shell", "status": "needs_confirmation",
                    "command": cmd, "error": "destructive command — confirm to run"}
        try:
            proc = subprocess.run(  # noqa: S602
                cmd, shell=True, capture_output=True, text=True,
                timeout=self.timeout, cwd=str(self.root),
            )
            return {"ok": proc.returncode == 0, "kind": "shell", "command": cmd,
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-2000:]}
        except subprocess.TimeoutExpired:
            return {"ok": False, "kind": "shell", "command": cmd, "error": "timeout"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "kind": "shell", "command": cmd, "error": str(exc)}

    # -- file write ----------------------------------------------------------
    def _file_write(self, params: Dict[str, Any]) -> Dict[str, Any]:
        raw_path = str(params.get("path", "")).strip()
        content = str(params.get("content", ""))
        mode = str(params.get("mode", "create")).strip().lower()
        if not raw_path:
            return {"ok": False, "kind": "file_write", "error": "path required"}
        try:
            target = restrict_to_sandbox(str(self.root), raw_path)
        except ValueError as exc:
            return {"ok": False, "kind": "file_write", "path": raw_path, "error": str(exc)}
        try:
            if mode == "append":
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "a", encoding="utf-8") as f:
                    f.write(content)
            elif mode == "overwrite":
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            else:  # create
                if target.exists():
                    return {"ok": False, "kind": "file_write", "path": raw_path,
                            "error": "file exists (use mode overwrite/append)"}
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "kind": "file_write", "path": raw_path, "error": str(exc)}
        rel = target.relative_to(self.root) if str(self.root) in str(target) else target
        return {"ok": True, "kind": "file_write", "path": str(rel),
                "mode": mode, "bytes": len(content.encode("utf-8"))}

    # -- create agent --------------------------------------------------------
    def _create_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = self._safe_name(str(params.get("name", "")))
        if not name:
            return {"ok": False, "kind": "create_agent", "error": "name required"}
        desc = str(params.get("description", f"{name} agent")).replace('"', "'")
        emoji = str(params.get("emoji", "🤖"))[:4] or "🤖"
        cls = name.capitalize() + "Agent"
        base = self.root / "kage" / "agents" / name
        if base.exists():
            return {"ok": False, "kind": "create_agent", "name": name,
                    "error": "agent already exists"}
        try:
            base.mkdir(parents=True)
            (base / "__init__.py").write_text(_AGENT_INIT.format(cls=cls), encoding="utf-8")
            (base / "agent.py").write_text(
                _AGENT_TEMPLATE.format(name=name, cls=cls, desc=desc, emoji=emoji),
                encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "kind": "create_agent", "name": name, "error": str(exc)}
        return {"ok": True, "kind": "create_agent", "name": name, "class": cls,
                "path": str(base.relative_to(self.root)),
                "register": f'kage.agents.{name}.agent:{cls}'}

    @staticmethod
    def _safe_name(name: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "", name).strip("_").lower()
        return cleaned[:32]


_AGENT_INIT = '''"""{cls} — auto-generated by Kage."""
from __future__ import annotations
from .agent import {cls}
__all__ = ["{cls}"]
'''

_AGENT_TEMPLATE = '''"""agents/{name}/agent.py — auto-generated by Kage. Customize me!"""

from __future__ import annotations
from typing import Any, Dict

from ...core.base_agent import BaseAgent


class {cls}(BaseAgent):
    name = "{name}"
    kind = "{name}"
    description = "{desc}"
    emoji = "{emoji}"

    def wake(self) -> None:
        self._awake = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: implement this agent's real capability.
        return {{"ok": True, "agent": self.name, "note": "auto-generated; customize me"}}

    def sleep(self) -> None:
        self._awake = False
'''


def format_results(results: List[Dict[str, Any]]) -> str:
    """Render executed action results as a concise, transport-friendly block."""
    if not results:
        return ""
    lines = ["", "— action results —"]
    for r in results:
        kind = r.get("kind", "?")
        if kind == "shell":
            tag = f"[shell] {r.get('command', '')}"
            if r.get("status") in ("needs_confirmation", "forbidden"):
                lines.append(f"⚠ {tag} → {r.get('status')}: {r.get('error', '')}")
                continue
            out = (r.get("stdout") or "").strip()
            err = (r.get("stderr") or "").strip()
            lines.append(f"{tag}  (exit {r.get('exit_code', '?')})")
            if out:
                lines.append(out)
            if err:
                lines.append(f"[stderr] {err}")
        elif kind == "file_write":
            mark = "✏" if r.get("ok") else "⚠"
            lines.append(f"{mark} [file_write] {r.get('path', '')} ({r.get('mode', '?')})"
                         + (f" → {r.get('error', '')}" if not r.get("ok") else f" · {r.get('bytes', 0)}b"))
        elif kind == "create_agent":
            mark = "🆕" if r.get("ok") else "⚠"
            extra = f" → {r.get('error', '')}" if not r.get("ok") else f" · {r.get('path', '')}"
            lines.append(f"{mark} [create_agent] {r.get('name', '')}{extra}")
        elif kind == "reply":
            if r.get("text"):
                lines.append(r["text"])
        else:
            lines.append(f"[{kind}] {'ok' if r.get('ok') else r.get('error', 'error')}")
    return "\n".join(lines).strip()
