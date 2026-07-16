"""
Core Features package for KAGE OS.
Built-in features available to all agents and Kage supervisor context:
- Browser-Use (Web searching & scraping)
- OpenHands (Sandboxed code execution & software editing)
- MCP Engine (Model Context Protocol client & server interface)
- CrewAI (Multi-role agent crew orchestrator)
"""

from .browser import BrowserFeature
from .openhands import OpenHandsFeature
from .mcp import MCPFeature
from .crew import CrewFeature

__all__ = ["BrowserFeature", "OpenHandsFeature", "MCPFeature", "CrewFeature"]
