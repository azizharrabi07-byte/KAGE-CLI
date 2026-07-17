#!/usr/bin/env python3
"""
autocomplete.py — Command Autocompletion Engine for KAGE OS REPL.
Integrates with readline tab-completion for slash commands, agents, and subcommands.
Part of Phase 6 Production CLI Engine.
"""

import readline
from typing import List, Optional

COMMAND_SUGGESTIONS = [
    "/help",
    "/models",
    "/models --all",
    "/providers",
    "/config list",
    "/config get ",
    "/config set ",
    "/status",
    "/health",
    "/agents",
    "/traces",
    "/schedules",
    "/logs",
    "/clear",
    "/exit",
    "kage status",
    "kage health",
    "kage logs",
    "kage schedule list",
    "kage telegram start",
    "kage telegram status",
    "kage telegram stop",
]


class CLICompleter:
    """Readline tab completion handler."""

    def __init__(self, commands: Optional[List[str]] = None):
        self.commands = commands or COMMAND_SUGGESTIONS
        self.matches: List[str] = []

    def complete(self, text: str, state: int) -> Optional[str]:
        if state == 0:
            if text:
                self.matches = [c for c in self.commands if c.startswith(text)]
            else:
                self.matches = list(self.commands)

        if state < len(self.matches):
            return self.matches[state]
        return None

    def setup_readline(self):
        """Bind completion to Tab key in readline."""
        try:
            readline.set_completer(self.complete)
            readline.parse_and_bind("tab: complete")
        except Exception:
            pass
