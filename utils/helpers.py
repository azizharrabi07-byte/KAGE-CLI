"""
utils/helpers.py
Small shared helpers: safe JSON parsing, text chunking, env defaults.
"""

import json
from typing import Any, List, Optional


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Parse JSON leniently, returning ``default`` on failure."""
    if default is None:
        default = {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def chunk_text(text: str, size: int = 4000) -> List[str]:
    """Split text into <= size chunks (e.g. for Telegram's 4096-char limit)."""
    if not text:
        return []
    return [text[i:i + size] for i in range(0, len(text), size)]


def env_bool(name: str, default: bool = False) -> bool:
    import os
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def first_non_empty(*values: Optional[str]) -> Optional[str]:
    """Return the first non-None, non-empty string, else None."""
    for value in values:
        if value:
            return value
    return None
