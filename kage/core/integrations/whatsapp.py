"""core/integrations/whatsapp.py — WhatsApp bridge client (Baileys REST).

Connects to a local Node bridge (@whiskeysockets/baileys), requests QR / restores
session, sends messages, polls inbound. Degrades gracefully when the bridge is
absent. Auth from env only (WHATSAPP_BRIDGE_URL / WHATSAPP_BRIDGE_TOKEN).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from urllib import error, request

from ..result import ToolResult
from .base_integration import BaseIntegration


class WhatsAppIntegration(BaseIntegration):
    name = "whatsapp"
    kind = "whatsapp"

    def __init__(self, *, config: Optional[Dict[str, Any]] = None,
                 bridge_url: Optional[str] = None, token: Optional[str] = None,
                 **kwargs: Any) -> None:
        super().__init__(config=config, **kwargs)
        cfg = self.config
        self.bridge_url = (bridge_url or cfg.get("bridge_url")
                           or os.environ.get("WHATSAPP_BRIDGE_URL")
                           or "http://127.0.0.1:3000").rstrip("/")
        self.token = token or cfg.get("token") or os.environ.get("WHATSAPP_BRIDGE_TOKEN", "")
        self.session_id = cfg.get("session_id") or os.environ.get("WHATSAPP_SESSION_ID", "kage")

    def connect(self) -> ToolResult:
        res = self._http("GET", f"/{self.session_id}/health")
        if res.ok:
            self._connected = True
            data = res.data if isinstance(res.data, dict) else {}
            return ToolResult.success({"status": "connected",
                                       "authenticated": data.get("authenticated", False)})
        return res

    def _alive(self) -> bool:
        return self._http("GET", f"/{self.session_id}/health").ok

    def request_qr(self) -> Any:
        res = self._http("GET", f"/{self.session_id}/qr")
        return res.data if res.ok else None

    def restore_session(self) -> Any:
        res = self._http("POST", f"/{self.session_id}/restore")
        self._connected = res.ok
        return res.data if res.ok else None

    def _send(self, payload: Dict[str, Any]) -> Any:
        to = str(payload.get("to", ""))
        text = str(payload.get("text", ""))
        if not to or not text:
            raise ValueError("'to' and 'text' are required")
        body = json.dumps({"to": to, "text": text}).encode("utf-8")
        res = self._http("POST", f"/{self.session_id}/send", body=body)
        return res.data

    def _receive(self, payload: Dict[str, Any]) -> Any:
        res = self._http("GET", f"/{self.session_id}/messages",
                         query={"since": str(payload.get("since", ""))})
        return res.data

    def _http(self, method: str, path: str, *, body: Optional[bytes] = None,
              query: Optional[Dict[str, str]] = None) -> ToolResult:
        from urllib.parse import urlencode
        url = self.bridge_url + path
        if query:
            url += "?" + urlencode({k: v for k, v in query.items() if v})
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = request.Request(url, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=min(self.timeout, 15.0)) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8", "replace")
                return ToolResult.success(json.loads(raw) if raw else {})
        except error.HTTPError as exc:
            return ToolResult.failure(f"bridge HTTP {exc.code}: {exc.reason}")
        except (error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            return ToolResult.failure(f"bridge unreachable: {exc}")
        except json.JSONDecodeError as exc:
            return ToolResult.failure(f"bridge bad JSON: {exc}")
