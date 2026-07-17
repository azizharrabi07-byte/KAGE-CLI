#!/usr/bin/env python3
"""
user_memory.py — Persistent per-user memory store for KAGE OS.
Stores user facts, names, preferences, and key-value attributes in ~/.kage/memory.json.
Keyed by user_id (e.g., Telegram chat_id or 'default' local user).
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

MEMORY_FILE = Path.home() / ".kage" / "memory.json"
_lock = threading.Lock()


def _get_memory_path() -> Path:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    return MEMORY_FILE


def load_all_memories() -> Dict[str, Any]:
    """Load full memory file contents."""
    path = _get_memory_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_all_memories(data: Dict[str, Any]) -> bool:
    """Save full memory dictionary to JSON file atomically."""
    path = _get_memory_path()
    with _lock:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception:
            return False


def get_user_memory(user_id: str = "default") -> Dict[str, Any]:
    """Retrieve memory block for a specific user ID."""
    str_uid = str(user_id)
    all_m = load_all_memories()
    user_data = all_m.get(str_uid, {
        "name": None,
        "facts": [],
        "kv": {},
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
    })
    return user_data


def save_user_memory(user_id: str, user_data: Dict[str, Any]) -> bool:
    """Save memory block for a specific user ID."""
    str_uid = str(user_id)
    all_m = load_all_memories()
    user_data["last_updated"] = datetime.now().isoformat()
    all_m[str_uid] = user_data
    return save_all_memories(all_m)


def add_user_fact(user_id: str, fact: str) -> bool:
    """Store a fact about a user."""
    str_uid = str(user_id)
    u_mem = get_user_memory(str_uid)
    facts = u_mem.get("facts", [])
    if not isinstance(facts, list):
        facts = []
    if fact not in facts:
        facts.append(fact)
    u_mem["facts"] = facts
    return save_user_memory(str_uid, u_mem)


def set_user_name(user_id: str, name: str) -> bool:
    """Set preferred name for a user."""
    str_uid = str(user_id)
    u_mem = get_user_memory(str_uid)
    u_mem["name"] = name
    return save_user_memory(str_uid, u_mem)


def set_user_kv(user_id: str, key: str, value: Any) -> bool:
    """Set a key-value attribute for a user."""
    str_uid = str(user_id)
    u_mem = get_user_memory(str_uid)
    kv = u_mem.get("kv", {})
    if not isinstance(kv, dict):
        kv = {}
    kv[key] = value
    u_mem["kv"] = kv
    return save_user_memory(str_uid, u_mem)


def format_user_memory_prompt(user_id: str = "default") -> str:
    """Format user memory into prompt context instructions for LLM brain."""
    str_uid = str(user_id)
    u_mem = get_user_memory(str_uid)

    name = u_mem.get("name")
    facts = u_mem.get("facts", [])
    kv = u_mem.get("kv", {})

    if not name and not facts and not kv:
        return f"[User Context for User ID {str_uid}]: No previously stored information."

    lines = [f"[Persistent Memory for User ID {str_uid}]:"]
    if name:
        lines.append(f"• User Name: {name}")
    if facts:
        lines.append("• Known Facts:")
        for f in facts:
            lines.append(f"  - {f}")
    if kv:
        lines.append("• Saved Attributes:")
        for k, v in kv.items():
            lines.append(f"  - {k}: {v}")

    return "\n".join(lines)
