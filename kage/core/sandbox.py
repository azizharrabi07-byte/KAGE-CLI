"""core/sandbox.py — input validation + sandboxed shell execution (Phase 6).

User input is sanitised before it reaches a shell or an LLM. Shell commands are
validated against an allow-list and executed inside a fresh temporary directory
with a hard timeout. ``dry_run`` returns the validation verdict without
executing.
"""

from __future__ import annotations

import re
import shlex
import subprocess
import tempfile
from typing import Any, Dict

from .result import ToolResult

MAX_INPUT = 4000

_FORBIDDEN = [
    re.compile(r"(^|;|\s)\s*rm\s+-rf?\s+/"),
    re.compile(r":\(\)\s*\{"),
    re.compile(r"\b(curl|wget)\b", re.IGNORECASE),
    re.compile(r"\b(nc|bash|sh|zsh|dash)\b\s+-c", re.IGNORECASE),
    re.compile(r"\$\("),
    re.compile(r"`"),
    re.compile(r"\b(mkfs|dd)\s+if=", re.IGNORECASE),
    re.compile(r"\b(shutdown|reboot)\b", re.IGNORECASE),
]

_ALLOWED = {
    "ls", "cat", "pwd", "echo", "wc", "grep", "head", "tail", "date",
    "whoami", "uname", "stat", "file", "find", "sort", "uniq", "env",
}


def sanitize(text: str) -> str:
    """Strip control/null bytes, drop CR, cap length."""
    cleaned = re.sub(r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]", "", text or "")
    return cleaned.replace("\r", "").strip()[:MAX_INPUT]


def validate_command(raw: str) -> ToolResult:
    cmd = sanitize(raw)
    if not cmd:
        return ToolResult.failure("empty command")
    for pat in _FORBIDDEN:
        if pat.search(cmd):
            return ToolResult.failure(f"blocked by sandbox policy: matched {pat.pattern}")
    parts = shlex.split(cmd)
    bin_ = parts[0] if parts else ""
    if bin_ not in _ALLOWED:
        return ToolResult.failure(f"command '{bin_}' is not in the allow-list")
    if any(a.startswith("/") for a in parts[1:]):
        return ToolResult.failure("absolute paths are not permitted in the sandbox")
    return ToolResult.success({"command": bin_, "args": parts[1:], "sandbox": "/tmp/kage-sandbox"})


def run(raw_command: str, *, dry_run: bool = False, timeout: float = 5.0) -> ToolResult:
    """Validate then (optionally) execute a command in a temp sandbox."""
    validation = validate_command(raw_command)
    if not validation.ok:
        validation.meta["stage"] = "validation"
        return validation
    spec: Dict[str, Any] = validation.data
    if dry_run:
        return ToolResult.success({"executed": False, "dry_run": True,
                                   "validation": validation.to_dict()})
    sandbox = tempfile.mkdtemp(prefix="kage-sandbox-")
    try:
        proc = subprocess.run([spec["command"], *spec["args"]], cwd=sandbox,
                              capture_output=True, text=True, timeout=timeout, check=False)
        return ToolResult.success({
            "executed": True, "stdout": proc.stdout, "stderr": proc.stderr,
            "exit_code": proc.returncode, "sandbox": sandbox,
        })
    except subprocess.TimeoutExpired:
        return ToolResult.failure(f"timeout after {timeout}s")
    except FileNotFoundError as exc:
        return ToolResult.failure(str(exc))
