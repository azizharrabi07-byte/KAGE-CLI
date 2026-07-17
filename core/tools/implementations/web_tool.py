#!/usr/bin/env python3
"""
web_tool.py — Web Search & Page Fetching Tool Wrapper.
Part of Phase 8 Tool Framework.
"""

from typing import Dict, Any
from core.features import BrowserFeature
from core.tools.base import BaseTool, ToolMetadata, PermissionLevel
from core.tools.registry import ToolRegistry


class WebTool(BaseTool):
    """Executes live web searches and URL page fetching."""

    def __init__(self):
        super().__init__(ToolMetadata(
            name="web_search",
            description="Searches the web or fetches web page text",
            category="web",
            permission_level=PermissionLevel.SAFE,
            parameters_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "search | fetch"},
                    "query": {"type": "string", "description": "Search query or target URL"}
                },
                "required": ["action", "query"]
            }
        ))
        self.browser = BrowserFeature()

    def run(self, args: Dict[str, Any]) -> Any:
        action = args["action"]
        query = args["query"]

        if action == "search":
            return self.browser.search(query)
        elif action == "fetch":
            return self.browser.fetch(query)
        else:
            raise ValueError(f"Unknown web_search action: '{action}'")


ToolRegistry.register(WebTool())
