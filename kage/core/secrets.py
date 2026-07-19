"""core/secrets.py — secret management (Phase 6).

Secrets are read from the environment ONLY and are never persisted to disk or
written to logs. This module provides masking, a registry of the keys the OS
expects (so ``kage secrets list`` works), log-scrubbing patterns, and helpers
to add/remove secrets in the *current process* environment (e.g. loaded from a
git-ignored ``.env`` via python-dotenv).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

# Known secret keys the OS expects, grouped by scope.
KNOWN_SECRETS: Dict[str, List[str]] = {
    "discord": ["DISCORD_BOT_TOKEN", "DISCORD_WEBHOOK_URL"],
    "telegram": ["TELEGRAM_BOT_TOKEN"],
    "llm": ["LLM_API_KEY", "WEB_SEARCH_API_KEY"],
}


def mask(value: str) -> str:
    """Return a masked representation, e.g. ``••••••4f2a``."""
    if not value:
        return ""
    tail = value[-4:]
    return "•" * min(max(len(value) - 4, 4), 24) + tail


@dataclass
class SecretRecord:
    key: str
    scope: str
    set: bool
    masked: str

    def to_dict(self) -> Dict[str, object]:
        return {"key": self.key, "scope": self.scope, "set": self.set, "masked": self.masked}


def resolve(key: str) -> Optional[str]:
    """Read a secret from the environment only."""
    return os.environ.get(key)


def list_secrets() -> List[SecretRecord]:
    out: List[SecretRecord] = []
    for scope, keys in KNOWN_SECRETS.items():
        for key in keys:
            val = resolve(key)
            out.append(SecretRecord(key=key, scope=scope, set=bool(val),
                                    masked=mask(val) if val else ""))
    return out


# Patterns scrubbed from any log line before it is written (defence in depth).
SECRET_PATTERNS = [
    re.compile(r"(sk-|tok_?|api[_-]?key)[\"' :=]+[A-Za-z0-9_\-]{8,}", re.IGNORECASE),
    re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b"),
]


def scrub(text: str) -> str:
    for pat in SECRET_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


def add_secret(key: str, value: str) -> str:
    """Set a value in the *current process* environment only (never to disk)."""
    os.environ[key] = value
    return mask(value)


def remove_secret(key: str) -> bool:
    if key in os.environ:
        os.environ.pop(key, None)
        return True
    return False
