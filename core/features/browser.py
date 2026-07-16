#!/usr/bin/env python3
"""
Browser-Use Feature — Native Web Searching, Page Fetching & Link Extraction for KAGE OS.
Available to all agents and brain via context.browser
Reference: https://github.com/browser-use/browser-use
"""

import json
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse, quote_plus, parse_qs


class BrowserFeature:
    """Built-in Web Browsing & Search Feature."""

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """Perform a web search using DuckDuckGo HTML parser."""
        import requests

        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(search_url, headers=headers, timeout=10)
        resp.raise_for_status()

        html = resp.text
        results = []

        matches = re.findall(
            r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>\s*(.*?)\s*</a>[\s\S]*?<a class="result__snippet[^"]*"[^>]*>([\s\S]*?)</a>',
            html,
            re.IGNORECASE,
        )

        for match in matches[:max_results]:
            raw_url, title, snippet = match
            clean_title = re.sub(r"<[^>]+>", "", title).strip()
            clean_snippet = re.sub(r"<[^>]+>", "", snippet).strip()

            if "uddg=" in raw_url:
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
            links = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html)
            for link, title in links[:max_results]:
                results.append({
                    "title": re.sub(r"<[^>]+>", "", title).strip(),
                    "url": link,
                    "snippet": "",
                })

        return results

    def fetch(self, url: str) -> Dict:
        """Fetch target URL content and extract clean readable text."""
        import requests

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

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
            "text": clean_text[:4000],
            "total_length": len(clean_text),
        }

    def extract_links(self, url: str) -> Dict:
        """Extract all external/internal hyperlinks from webpage."""
        import requests

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

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
