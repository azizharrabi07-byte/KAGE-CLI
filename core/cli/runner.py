#!/usr/bin/env python3
"""
runner.py — Standardized Execution Context & Flag Parser for KAGE OS CLI.
Supports --dry-run, --debug, --verbose, --json, and --yaml execution flags.
Part of Phase 6 Production CLI Engine.
"""

import json
import logging
import sys
from dataclasses import dataclass
from typing import Dict, Any, Optional
from .formatter import OutputFormatter

logger = logging.getLogger("kage.cli_runner")


@dataclass
class ExecutionFlags:
    """Standardized CLI command execution options."""
    dry_run: bool = False
    debug: bool = False
    verbose: bool = False
    format_output: str = "text"  # text, json, yaml
    batch_mode: bool = False


class CommandRunner:
    """Executes supervisor commands evaluating CLI flags (dry-run, output formats, debug logs)."""

    def __init__(self, supervisor=None, flags: Optional[ExecutionFlags] = None):
        self.supervisor = supervisor
        self.flags = flags or ExecutionFlags()

        if self.flags.debug:
            logging.basicConfig(level=logging.DEBUG)
        elif self.flags.verbose:
            logging.basicConfig(level=logging.INFO)

    def run(self, command: str, args: Dict[str, Any]) -> str:
        """Execute command or simulate in dry-run mode, returning formatted string output."""
        if self.flags.dry_run:
            simulated = {
                "status": "dry_run",
                "simulated_command": command,
                "args": args,
                "message": "[DRY-RUN MODE] Operation simulated without live state side-effects."
            }
            return OutputFormatter.format_output(simulated, self.flags.format_output)

        if not self.supervisor:
            err = {"status": "error", "error": "Supervisor reference unavailable."}
            return OutputFormatter.format_output(err, self.flags.format_output)

        result = self.supervisor.process_command(command, args)
        return OutputFormatter.format_output(result, self.flags.format_output)
