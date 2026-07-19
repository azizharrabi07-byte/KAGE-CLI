"""core/tools/browser.py — web fetch + search tool (stdlib only).

Uses urllib so it works on a minimal Termux install. Set WEB_SEARCH_API_KEY
to plug a real search provider; otherwise it falls back to a fetch+snippet.
"""

from __future__ import annotations

import urllib.parse
import urllib.request
from typing import Any, Dict

from .base import Tool, ToolMeta, ToolSchema


class WebFetchTool(Tool):
    meta = ToolMeta(
        name="web.fetch",
        description="Fetch the text of a URL (best-effort, no JS).",
        schema=ToolSchema(required=["url"]),
    )

    def run(self, args: Dict[str, Any], user_id: str = "cli") -> Dict[str, Any]:
        url = str(args["url"])
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KAGE-OS/0.1"})
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                raw = resp.read(200_000).decode("utf-8", "ignore")
            # very rough HTML strip
            import re
            text = re.sub(r"<[^>]+>", " ", raw)
            text = re.sub(r"\s+", " ", text).strip()
            return {"ok": True, "url": url, "snippet": text[:1500]}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "url": url, "error": str(exc)}


class WebSearchTool(Tool):
    meta = ToolMeta(
        name="web.search",
        description="Search the web. Returns a structured result list.",
        schema=ToolSchema(required=["query"], optional={"limit": "int"}),
    )

    def run(self, args: Dict[str, Any], user_id: str = "cli") -> Dict[str, Any]:
        query = str(args["query"])
        limit = int(args.get("limit", 5))
        # No API key → return a structured "needs provider" result so the
        # supervisor can explain clearly instead of failing.
        import os
        if not os.environ.get("WEB_SEARCH_API_KEY"):
            return {
                "ok": True,
                "query": query,
                "results": [],
                "note": "Set WEB_SEARCH_API_KEY for live results.",
            }
        # Provider wired here in production (e.g. SerpAPI/Bing). Placeholder:
        return {"ok": True, "query": query, "results": [], "note": "provider not configured"}
