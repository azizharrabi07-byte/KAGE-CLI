"""core/integrations/obsidian.py — Obsidian Local REST API integration.

Talks to the Obsidian "Local REST API" plugin. Uses only the standard library
(``urllib``) and degrades gracefully when the plugin/token is unavailable.
Self-signed localhost cert => unverified context. Token from env only.
"""

from __future__ import annotations

import json
import os
import ssl
from typing import Any, Dict, Optional
from urllib import error, request

from ..result import ToolResult
from .base_integration import BaseIntegration


class ObsidianIntegration(BaseIntegration):
    name = "obsidian"
    kind = "obsidian"

    def __init__(self, *, config: Optional[Dict[str, Any]] = None,
                 base_url: Optional[str] = None, token: Optional[str] = None,
                 **kwargs: Any) -> None:
        super().__init__(config=config, **kwargs)
        cfg = self.config
        self.base_url = (base_url or cfg.get("base_url")
                         or os.environ.get("OBSIDIAN_BASE_URL")
                         or "https://127.0.0.1:27124").rstrip("/")
        self.token = token or cfg.get("token") or os.environ.get("OBSIDIAN_TOKEN", "")
        self._ctx = ssl._create_unverified_context()

    def connect(self) -> ToolResult:
        if not self.token:
            return ToolResult.failure("missing OBSIDIAN_TOKEN")
        res = self._request("GET", "/")
        if res.ok:
            self._connected = True
            data = res.data or {}
            return ToolResult.success({"status": "connected",
                                       "vault": data.get("vault") if isinstance(data, dict) else None})
        return res

    def _alive(self) -> bool:
        return bool(self.token)

    def _send(self, payload: Dict[str, Any]) -> Any:
        path = payload.get("path", "")
        content = payload.get("content", "")
        if not path:
            raise ValueError("path is required")
        return self._request("PUT", f"/vault/{path}", body=content,
                             content_type="text/markdown").data

    def _receive(self, payload: Dict[str, Any]) -> Any:
        return self.list_files()

    def list_files(self) -> Any:
        res = self._request("GET", "/vault/")
        if not res.ok:
            return None
        data = res.data
        if isinstance(data, dict) and "files" in data:
            return [f.get("path", f) if isinstance(f, dict) else f for f in data["files"]]
        return data

    def read_file(self, path: str) -> Any:
        return self._request("GET", f"/vault/{path}", content_type="text/markdown").data

    def append_file(self, path: str, content: str) -> Any:
        return self._request("POST", f"/vault/{path}", body=content,
                             content_type="text/markdown").data

    def search(self, query: str, *, limit: int = 20) -> Any:
        from urllib.parse import quote
        url = f"/search/simple/?query={quote(query)}&contextLength=0&limit={limit}"
        res = self._request("GET", url)
        return res.data if res.ok else None

    def _request(self, method: str, path: str, *, body: Optional[str] = None,
                 content_type: str = "application/json") -> ToolResult:
        if not self.token:
            return ToolResult.failure("missing OBSIDIAN_TOKEN")
        url = self.base_url + path
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": content_type}
        data = body.encode("utf-8") if body is not None else None
        req = request.Request(url, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=min(self.timeout, 15.0), context=self._ctx) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8", "replace")
                if content_type == "text/markdown" or not raw:
                    return ToolResult.success(raw)
                return ToolResult.success(json.loads(raw))
        except error.HTTPError as exc:
            return ToolResult.failure(f"obsidian HTTP {exc.code}: {exc.reason}")
        except (error.URLError, TimeoutError, OSError) as exc:
            return ToolResult.failure(f"obsidian unreachable: {exc}")
        except json.JSONDecodeError as exc:
            return ToolResult.failure(f"obsidian bad JSON: {exc}")
