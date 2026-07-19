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
    """Return the command if safe, else raise ValueError."""
    cmd = cmd.strip()
    if not cmd:
        raise ValueError("empty command")
    if re.search(r"[;&|>`$]", cmd) and not cmd.startswith("echo"):
        # allow simple pipelines later; block for now unless allow_destructive
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
