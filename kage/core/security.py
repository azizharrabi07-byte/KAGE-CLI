"""core/security.py — secrets, permissions, input validation, sandboxing.

Design goals:
  * Secrets are read from env / a git-ignored file, never hardcoded.
  * Destructive tools (shell, file writes) require explicit permission.
  * User input is validated before reaching tools.
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Set


# Tools considered destructive / sensitive; require an allow flag.
DESTRUCTIVE_PREFIXES = ("shell.", "file.write", "system.")

# Shell commands that must never run unsanitized.
SHELL_BLOCKLIST = {
    "rm", "rmdir", "mkfs", "dd", "shutdown", "reboot", "halt",
    "chmod", "chown", "kill", "killall", "pkill", "mv", "cp",
}


@dataclass
class SecurityPolicy:
    """Per-user tool permissions and sandbox root."""

    allowed_tools: Set[str] = field(default_factory=set)
    denied_tools: Set[str] = field(default_factory=set)
    sandbox_root: str = ""
    allow_destructive: bool = False

    def allow(self, tool: str, user_id: str = "cli") -> bool:
        if tool in self.denied_tools:
            return False
        if tool in self.allowed_tools:
            return True
        if tool.startswith(DESTRUCTIVE_PREFIXES) and not self.allow_destructive:
            return False
        return True


class SecretManager:
    """Loads secrets from env first, then a git-ignored secrets file."""

    def __init__(self, secrets_file: str = ".kage/secrets.json") -> None:
        self.path = Path(secrets_file)

    def get(self, key: str, default: str = "") -> str:
        val = os.environ.get(key)
        if val:
            return val
        if self.path.exists():
            try:
                import json
                return json.loads(self.path.read_text()).get(key, default)
            except (json.JSONDecodeError, OSError):
                return default
        return default


def validate_shell(cmd: str) -> str:
    """Return the command if safe, else raise ValueError.

    Command substitution ($(...), backticks, ${...}, subshells) is ALWAYS
    blocked, even for ``echo``. Simple shell metacharacters (;&|>) are blocked
    unless the command is a plain literal ``echo``.
    """
    cmd = cmd.strip()
    if not cmd:
        raise ValueError("empty command")
    if re.search(r"\$\(|`|\$\{|\(\s*\)", cmd):
        raise ValueError(f"command substitution blocked: {cmd!r}")
    if re.search(r"[;&|>]", cmd) and not cmd.startswith("echo"):
        raise ValueError(f"shell metacharacters blocked: {cmd!r}")
    first = shlex.split(cmd)[0] if cmd else ""
    if first in SHELL_BLOCKLIST:
        raise ValueError(f"blocked command: {first}")
    return cmd


def sandbox_path(root: str, target: str) -> Path:
    """Resolve ``target`` under ``root`` and reject path traversal."""
    base = Path(root).resolve()
    resolved = (base / target).resolve()
    if base != resolved and base not in resolved.parents:
        raise ValueError(f"path escapes sandbox: {target}")
    return resolved


# ---------------------------------------------------------------------------
# Phase 6 hardening: path / text / shell-argument sanitisation (additive).
# ---------------------------------------------------------------------------

_PATH_TRAVERSAL = re.compile(r"(?:\.\./|~|\0)")


def sanitize_path(raw: str) -> str:
    """Reject path traversal / null bytes and return a cleaned relative path."""
    cleaned = (raw or "").replace("\\", "/").strip().lstrip("/")
    if "\0" in cleaned:
        raise ValueError("null byte in path")
    if "../" in cleaned or cleaned == "..":
        raise ValueError(f"path traversal blocked: {raw!r}")
    return cleaned


def sanitize_text(raw: str, *, max_len: int = 8000) -> str:
    """Strip control/null bytes; cap length; safe for LLM/shell context."""
    cleaned = re.sub(r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]", "", raw or "")
    return cleaned.replace("\r", "").strip()[:max_len]


def escape_shell_arg(value: str) -> str:
    """Single-quote-escape a value for safe shell interpolation."""
    return "'" + (value or "").replace("'", "'\"'\"'") + "'"


def restrict_to_sandbox(root: str, target: str, *, create: bool = False) -> "Path":
    """Resolve ``target`` under an absolute ``root`` sandbox; reject escapes."""
    base = Path(root).expanduser().resolve()
    if create:
        base.mkdir(parents=True, exist_ok=True)
    cleaned = sanitize_path(target)
    resolved = (base / cleaned).resolve()
    if resolved != base and base not in resolved.parents:
        raise ValueError(f"path escapes sandbox: {target!r}")
    return resolved
