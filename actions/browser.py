"""
actions/browser.py
Web search and page fetching with deep research support.
"""

import re
import json
import requests
from urllib.parse import urlparse, parse_qs, unquote
from typing import List, Dict, Optional
from bs4 import BeautifulSoup


def get_final_url(url: str, timeout: int = 10) -> str:
    parsed = urlparse(url)
    if parsed.netloc in ("duckduckgo.com", "r.duckduckgo.com") and "uddg" in parse_qs(parsed.query):
        uddg = parse_qs(parsed.query).get("uddg", [""])[0]
        if uddg:
            return unquote(uddg)
    for param in ["url", "u", "redirect", "target", "link"]:
        if param in parse_qs(parsed.query):
            candidate = parse_qs(parsed.query).get(param, [""])[0]
            if candidate:
                return unquote(candidate)
    try:
        resp = requests.head(url, allow_redirects=True, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code < 400:
            return resp.url
    except Exception:
        pass
    return url


def extract_links_from_ddg(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", class_="result__a"):
        href = a.get("href", "")
        if href:
            final = get_final_url(href)
            if final and final not in links:
                links.append(final)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "uddg=" in href:
            final = get_final_url(href)
            if final and final not in links:
                links.append(final)
    return links


def fetch_page(url: str, timeout: int = 15) -> Dict:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        title = soup.find("title")
        title_text = title.get_text(strip=True) if title else "No title"
        main = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile("content|main", re.I))
        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)
        if len(text) > 8000:
            text = text[:8000] + "\n...[truncated]"
        return {"url": url, "title": title_text, "text": text, "status": "ok"}
    except Exception as e:
        return {"url": url, "title": "Error", "text": str(e), "status": "error"}


def search_duckduckgo(query: str, max_results: int = 5) -> List[Dict]:
    try:
        url = "https://html.duckduckgo.com/html/"
        resp = requests.post(url, data={"q": query}, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        links = extract_links_from_ddg(resp.text)
        results = []
        for link in links[:max_results]:
            final_url = get_final_url(link)
            results.append({"url": final_url, "title": "", "snippet": ""})
        soup = BeautifulSoup(resp.text, "html.parser")
        for i, result in enumerate(soup.find_all("div", class_="result")):
            if i >= max_results:
                break
            title_tag = result.find("a", class_="result__a")
            snippet_tag = result.find("a", class_="result__snippet")
            if title_tag and i < len(results):
                results[i]["title"] = title_tag.get_text(strip=True)
            if snippet_tag and i < len(results):
                results[i]["snippet"] = snippet_tag.get_text(strip=True)
        return results
    except Exception as e:
        return [{"url": "", "title": "Search Error", "snippet": str(e)}]


def deep_research(query: str, depth: int = 3) -> str:
    search_results = search_duckduckgo(query, max_results=depth)
    if not search_results or not search_results[0].get("url"):
        return "❌ Search failed. No results found."
    pages = []
    for result in search_results:
        url = result.get("url", "")
        if not url:
            continue
        page_data = fetch_page(url)
        if page_data["status"] == "ok":
            pages.append(page_data)
    if not pages:
        return "❌ Could not fetch any pages from search results."
    # Try to call LLM for synthesis
    try:
        from core.brain import call_llm
        prompt = f"Synthesize the following web sources into a comprehensive answer to: \"{query}\"\n\n"
        for i, page in enumerate(pages, 1):
            prompt += f"--- Source {i}: {page['title']} ({page['url']}) ---\n{page['text'][:2000]}\n\n"
        prompt += (
            "Instructions:\n1. Provide a well-structured summary.\n"
            "2. Cite sources by number [1], [2], etc.\n"
            "3. Highlight key findings and disagreements between sources.\n"
            "4. Keep it concise but thorough."
        )
        summary = call_llm(prompt, provider="groq")
        try:
            parsed = json.loads(summary)
            if "message" in parsed:
                summary = parsed["message"]
            elif "text" in parsed:
                summary = parsed["text"]
        except json.JSONDecodeError:
            pass
        return summary
    except Exception:
        lines = [f"🔍 Deep Research: {query}\n"]
        for i, page in enumerate(pages, 1):
            lines.append(f"\n**[{i}] {page['title']}**")
            lines.append(f"🔗 {page['url']}")
            lines.append(f"> {page['text'][:500]}...")
        lines.append("\n---")
        lines.append(f"Searched {len(pages)} sources. Use `depth=1` for quick answers.")
        return "\n".join(lines)


def browser_action(query: Optional[str] = None, url: Optional[str] = None, depth: int = 1) -> str:
    if url:
        page = fetch_page(url)
        if page["status"] == "ok":
            return f"**{page['title']}**\n\n{page['text'][:3000]}"
        return f"❌ Failed to fetch {url}: {page['text']}"
    if query:
        if depth <= 1:
            results = search_duckduckgo(query, max_results=3)
            lines = [f"🔍 Search: {query}\n"]
            for i, r in enumerate(results, 1):
                lines.append(f"\n**{i}. {r.get('title', 'No title')}**")
                lines.append(f"🔗 {r.get('url', '')}")
                lines.append(f"> {r.get('snippet', 'No snippet')}")
            return "\n".join(lines)
        else:
            return deep_research(query, depth=depth)
    return "❌ No query or URL provided."


if __name__ == "__main__":
    print(browser_action(query="latest AI news", depth=1)[:1000])
    print("\n=== Deep Research ===")
    print(browser_action(query="AI trends 2026", depth=2)[:1500])
