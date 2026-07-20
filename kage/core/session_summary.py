"""core/session_summary.py — generate concise session summaries."""

from __future__ import annotations

import re
from typing import Any, List, Optional


def summarize(messages: List[Any], llm: Optional[Any] = None,
              *, max_len: int = 120) -> str:
    """Return a one-line summary of the session's messages."""
    if not messages:
        return ""
    transcript_parts: List[str] = []
    for msg in messages[:8]:
        content = _get(msg, "content", "")
        role = _get(msg, "role", _get(msg, "author", ""))
        if content:
            transcript_parts.append(f"{role}: {content}")
    transcript = "\n".join(transcript_parts)
    if llm is not None:
        try:
            result = llm(f"Summarize this conversation in one sentence (max {max_len} chars).\n\n{transcript}")
            if result:
                return result.strip()[:max_len]
        except Exception:  # noqa: BLE001
            pass
    first_user = ""
    for msg in messages:
        if _get(msg, "role", "") == "user":
            first_user = _get(msg, "content", "")
            break
    if not first_user and transcript_parts:
        first_user = transcript_parts[0]
    summary = re.sub(r"\s+", " ", first_user).strip()
    if len(summary) > max_len:
        summary = summary[:max_len - 3] + "..."
    return summary or "Session started"


def _get(obj: Any, key: str, default: Any = "") -> Any:
    """Get a key from a dict, sqlite3.Row, or any object with key access."""
    try:
        return obj[key]
    except (KeyError, TypeError, IndexError):
        pass
    return getattr(obj, key, default)
