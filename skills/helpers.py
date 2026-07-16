#!/usr/bin/env python3
"""KAGE Skills — Shared utilities (hot-reloadable)"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union


def format_response(status: str, output: Any = None, error: Optional[str] = None) -> Dict[str, Any]:
    """Standard response format for all agents."""
    result = {"status": status}
    if output is not None:
        result["output"] = output
    if error:
        result["error"] = error
    return result


def parse_json_safe(text: str) -> Optional[Union[Dict, list]]:
    """Safely parse JSON from LLM or external text."""
    if not text or not isinstance(text, str):
        return None
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, TypeError):
        return None


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text for logging."""
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text


def load_json_file(path: Union[str, Path]) -> Optional[Dict]:
    """Safely load JSON file."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json_file(path: Union[str, Path], data: Any, indent: int = 4) -> bool:
    """Safely write data as JSON file."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, default=str)
        return True
    except Exception:
        return False
