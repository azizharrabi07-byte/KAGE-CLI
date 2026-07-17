#!/usr/bin/env python3
"""
formatter.py — Production Terminal Output Formatter for KAGE OS.
Provides TableFormatter, Spinner, and multi-format exporters (JSON, YAML, Text).
Part of Phase 6 Production CLI Engine.
"""

import json
import sys
import time
from typing import Dict, List, Optional, Any, Union


class TableFormatter:
    """Renders clean, aligned tables in plain text, ASCII, or Unicode style."""

    @staticmethod
    def render_table(headers: List[str], rows: List[List[Any]], title: str = "") -> str:
        if not rows:
            return f"No records found for {title}" if title else "Empty table."

        # Convert all cell values to string
        str_rows = [[str(cell) for cell in row] for row in rows]
        col_widths = [len(h) for h in headers]

        for row in str_rows:
            for idx, cell in enumerate(row):
                if idx < len(col_widths):
                    col_widths[idx] = max(col_widths[idx], len(cell))

        lines = []
        if title:
            lines.append(f"┌─── {title.upper()} ───┐")

        # Format header
        header_line = "  ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
        lines.append(header_line)
        lines.append("─" * len(header_line))

        # Format rows
        for row in str_rows:
            r_str = "  ".join(f"{cell:<{col_widths[i]}}" for i, cell in enumerate(row))
            lines.append(r_str)

        return "\n".join(lines)


class OutputFormatter:
    """Formats output payload based on execution flags (--json, --yaml, text)."""

    @staticmethod
    def format_output(data: Any, format_type: str = "text") -> str:
        format_type = format_type.lower() if format_type else "text"

        if format_type == "json":
            return json.dumps(data, indent=2, default=str)

        elif format_type in ("yaml", "yml"):
            return OutputFormatter._to_yaml(data)

        else:
            if isinstance(data, (dict, list)):
                return json.dumps(data, indent=2, default=str)
            return str(data)

    @staticmethod
    def _to_yaml(data: Any, depth: int = 0) -> str:
        """Lightweight YAML serializer without external dependencies."""
        indent = "  " * depth
        if isinstance(data, dict):
            lines = []
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{indent}{k}:")
                    lines.append(OutputFormatter._to_yaml(v, depth + 1))
                else:
                    lines.append(f"{indent}{k}: {v}")
            return "\n".join(lines)
        elif isinstance(data, list):
            lines = []
            for item in data:
                if isinstance(item, (dict, list)):
                    lines.append(f"{indent}-")
                    lines.append(OutputFormatter._to_yaml(item, depth + 1))
                else:
                    lines.append(f"{indent}- {item}")
            return "\n".join(lines)
        return f"{indent}{data}"


class Spinner:
    """CLI loading spinner for long-running operations."""

    def __init__(self, message: str = "Processing..."):
        self.message = message
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.idx = 0

    def tick(self):
        if sys.stdout.isatty():
            sys.stdout.write(f"\r{self.frames[self.idx % len(self.frames)]} {self.message}")
            sys.stdout.flush()
            self.idx += 1

    def stop(self):
        if sys.stdout.isatty():
            sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
            sys.stdout.flush()
