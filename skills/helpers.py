#!/usr/bin/env python3
"""KAGE Skills — Shared utilities (hot-reloadable)"""

from typing import Dict


def format_response(status: str, output: Any = None, error: str = None) -> Dict:
    """Standard response format for all agents."""
    result = {"status": status}
    if output is not None:
        result["output"] = output
    if error:
        result["error"] = error
    return result


def parse_json_safe(text: str) -> Optional[Dict]:
    """Safely parse JSON from LLM output."""
    import json
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text for logging."""
    return text[:max_len] + "..." if len(text) > max_len else text


from typing import Any, Dict, Optional