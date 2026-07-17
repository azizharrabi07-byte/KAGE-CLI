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
    "obsidian.read", "obsidian.search", "trace.list",
}

# Actions that need approval
SENSITIVE_ACTIONS = {
    "whatsapp.send", "obsidian.write", "obsidian.delete",
    "meta.upgrade", "system.delete", "system.install",
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

    # Auto-approve safe actions
    action_prefix = action.split(".")[0] + "." + action.split(".")[1] if "." in action else action
    if action_prefix in SAFE_ACTIONS or action in SAFE_ACTIONS:
        return True

    # Skip prompt if stdin is not a terminal (piped input)
    if not sys.stdin.isatty():
        return True

    # Prompt user
    desc = description or action
    print(f"\n⚠️  Permission required: {desc}", file=sys.stderr)
    try:
        response = input("Allow? [y/N] ").strip().lower()
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False
