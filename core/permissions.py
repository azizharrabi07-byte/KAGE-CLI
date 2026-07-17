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
    "obsidian.read", "obsidian.list_files", "obsidian.search",
    "browser.search", "browser.fetch", "browser.read", "browser.extract_links",
    "mcp.list_servers", "mcp.list_tools", "mcp.list_resources", "mcp.read_resource",
    "openhands.status",
    "whatsapp.status", "whatsapp.read",
    "trace.list", "trace.show", "schedule.list", "status",
}

# Actions that need approval
SENSITIVE_ACTIONS = {
    "whatsapp.send", "obsidian.write", "obsidian.append", "obsidian.delete",
    "mcp.call_tool", "openhands.execute_cmd", "openhands.run_python", "openhands.write_code",
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
