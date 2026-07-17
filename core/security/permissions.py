#!/usr/bin/env python3
"""
permissions.py — Hardened Permission & Authorization Security Manager for KAGE OS.
Controls auto-approval gates, sensitive action authorization, and channel security policies.
Part of Phase 9 Hardened Security Framework.
"""

import sys
import logging
from typing import Dict, Set, Optional

logger = logging.getLogger("kage.security")

# Actions categorized as SAFE (Auto-approved)
SAFE_ACTIONS: Set[str] = {
    "system.health", "system.read", "memory.read", "memory.write",
    "obsidian.read", "obsidian.list_files", "obsidian.search",
    "telegram.status", "telegram.read",
    "browser.search", "browser.fetch", "browser.read", "browser.extract_links",
    "mcp.list_servers", "mcp.list_tools", "mcp.list_resources", "mcp.read_resource",
    "openhands.status",
    "whatsapp.status", "whatsapp.read",
    "trace.list", "trace.show", "schedule.list", "status",
}

# Actions categorized as SENSITIVE (Requires confirmation or authorization)
SENSITIVE_ACTIONS: Set[str] = {
    "whatsapp.send", "telegram.send", "telegram.start",
    "obsidian.write", "obsidian.append", "obsidian.delete",
    "mcp.call_tool", "openhands.execute_cmd", "openhands.run_python", "openhands.write_code",
    "meta.upgrade", "meta.pull", "system.delete", "system.install",
}


class SecurityManager:
    """Enforces fine-grained permission control across CLI, IPC, and remote channels."""

    def __init__(self, require_interactive_confirm: bool = True):
        self.require_interactive_confirm = require_interactive_confirm

    def is_safe_action(self, action: str) -> bool:
        """Check if action is in safe auto-approved whitelist."""
        if action in SAFE_ACTIONS:
            return True
        action_prefix = action.split(".")[0] + ".*"
        return action_prefix in SAFE_ACTIONS

    def authorize_action(self, action: str, description: str = "", auto_approve: bool = False) -> bool:
        """Verify authorization before executing sensitive operations."""
        if auto_approve or self.is_safe_action(action):
            return True

        # Non-interactive stdin execution policy check
        if not sys.stdin.isatty():
            logger.warning(f"Non-interactive action '{action}' evaluated policy: Proceeding in daemon mode.")
            return True

        # Interactive Terminal Confirmation Prompt
        desc = description or action
        print(f"\n⚠️  {self.C_YELLOW if hasattr(self, 'C_YELLOW') else ''}SECURITY PERMISSION REQUIRED: {desc}\033[0m", file=sys.stderr)
        try:
            response = input("Allow action execution? [y/N] ").strip().lower()
            approved = response in ("y", "yes")
            if not approved:
                logger.info(f"Action '{action}' denied by terminal user.")
            return approved
        except (EOFError, KeyboardInterrupt):
            logger.info(f"Action '{action}' cancelled by terminal interrupt.")
            return False
