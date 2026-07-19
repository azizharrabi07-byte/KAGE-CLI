"""Optional tool wiring for the summarizer plugin."""
from __future__ import annotations


def register_tools(tool_manager) -> None:
    """No custom tools; relies on shared memory + search tools."""
    return None
