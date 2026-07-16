#!/usr/bin/env python3
"""
Browser Agent — Autonomous Web Search & Article Extraction Agent for KAGE OS.
Inspired by https://github.com/browser-use/browser-use
Actions: search, fetch, read, extract_links, browse
"""

import gc
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse, quote_plus


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False

    def wake(self, task_data: dict) -> dict:
        """Wake up: import networking and HTML parsing libraries."""
        global requests
        import requests as _requests
        requests = _requests

        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        action = task_data.get("action", "search")
        query = task_data.get("query", task_data.get("search", ""))
        url = task_data.get("url", "")
        max_results = task_data.get("max_results", 5)

        try:
            if action == "search":
                if not query:
                    return {"status": "error", "output": "Missing 'query' parameter for search"}
                results = self._search_web(query, max_results)
                return {"status": "done", "output": results}

            elif action in ("fetch", "read", "browse"):
                target_url = url or query
                if not target_url:
                    return {"status": "error", "output": "Missing 'url' parameter for fetch/browse"}
                if not target_url.startswith(("http://", "https://")):
                    target_url = "https://" + target_url

                content = self._fetch_url(target_url)
                return {"status": "done", "output": content}

            elif action == "extract_links":
                target_url = url or query
                if not target_url:
                    return {"status": "error", "output": "Missing 'url' parameter"}
                if not target_url.startswith(("http://", "https://")):
                    target_url = "https://" + target_url

                links = self._extract_links(target_url)
                return {"status": "done", "output": links}

            else:
                return {"status": "error", "output": f"Unknown action: {action}"}

        except Exception as e:
            return {"status": "error", "output": str(e)}

    def _search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """Perform a web search using HTML endpoint and extract top organic results."""
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(search_url, headers=headers, timeout=10)
        resp.raise_for_status()

        html = resp.text
        results = []

        # Parse organic links and titles from DuckDuckGo HTML
        matches = re.findall(
            r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>\s*(.*?)\s*</a>[\s\S]*?<a class="result__snippet[^"]*"[^>]*>([\s\S]*?)</a>',
            html,
            re.IGNORECASE,
        )

        for match in matches[:max_results]:
            raw_url, title, snippet = match
            clean_title = re.sub(r"<[^>]+>", "", title).strip()
            clean_snippet = re.sub(r"<[^>]+>", "", snippet).strip()

            # Clean DuckDuckGo redirect URLs
            if "uddg=" in raw_url:
                from urllib.parse import parse_qs
                parsed = parse_qs(urlparse(raw_url).query)
                real_url = parsed.get("uddg", [raw_url])[0]
            else:
                real_url = raw_url

            results.append({
                "title": clean_title,
                "url": real_url,
                "snippet": clean_snippet,
            })

        if not results:
            # Fallback regex matcher for title links
            links = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html)
            for link, title in links[:max_results]:
                results.append({
                    "title": re.sub(r"<[^>]+>", "", title).strip(),
                    "url": link,
                    "snippet": "",
                })

        return results

    def _fetch_url(self, url: str) -> Dict:
        """Fetch URL content and clean up readable text."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "").lower()
        if "json" in content_type:
            try:
                return {"url": url, "type": "json", "data": resp.json()}
            except Exception:
                pass

        html = resp.text
        # Clean HTML tags to extract clean text
        text = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        clean_lines = [line.strip() for line in text.split("\n") if line.strip()]
        clean_text = "\n".join(clean_lines)

        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE)
        page_title = title_match.group(1).strip() if title_match else url

        return {
            "url": url,
            "title": page_title,
            "text": clean_text[:4000],  # Truncate to safe LLM context budget
            "total_length": len(clean_text),
        }

    def _extract_links(self, url: str) -> Dict:
        """Extract all external/internal hyperlinks from target webpage."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        matches = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', resp.text, re.IGNORECASE)
        links = []
        seen = set()

        for link_url, text in matches:
            clean_text = re.sub(r"<[^>]+>", "", text).strip()
            if link_url not in seen and not link_url.startswith(("#", "javascript:", "mailto:")):
                seen.add(link_url)
                links.append({"url": link_url, "text": clean_text or link_url})

        return {"url": url, "total_links": len(links), "links": links[:30]}

    def sleep(self):
        self.alive = False
        gc.collect()
