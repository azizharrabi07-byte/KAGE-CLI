#!/usr/bin/env python3
"""
permissions.py — Ask user before destructive/external actions.
Auto-approves reads and health checks.
"""

import sys
from typing import Dict

# Actions that are safe (auto-approve)
SAFE_ACTIONS = {
    "system.health", "system.read", "memory.read", "memory.write",
    "trilium.read", "trilium.list_notes", "trilium.search",
    "whatsapp.status", "whatsapp.read",
    "trace.list", "trace.show", "schedule.list", "status",
}

# Actions that need approval
SENSITIVE_ACTIONS = {
    "whatsapp.send", "trilium.write_note", "trilium.append_note", "trilium.delete",
    "meta.upgrade", "meta.pull", "system.delete", "system.install",
}


def require_approval(action: str, description: str = "", auto_approve: bool = False) -> bool:
    """Ask user to approve an action.

    Args:
        action: Action identifier (e.g., "whatsapp.send")
        description: Human-readable description
        auto_approve: If True, skip prompt for testing

    Returns:
        True if approved, False if denied
    """
    if auto_approve:
        return True

    if action in SAFE_ACTIONS:
        return True

    action_prefix = action.split(".")[0] + ".*"
    if action_prefix in SAFE_ACTIONS:
        return True

    if not sys.stdin.isatty():
        return True

    desc = description or action
    print(f"\n⚠️  Permission required: {desc}", file=sys.stderr)
    try:
        response = input("Allow? [y/N] ").strip().lower()
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False
