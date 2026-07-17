#!/usr/bin/env python3
"""
telegram.py — Telegram Bot API Integration Provider.
"""

import time
from typing import Dict, Any
from core.integrations.base import AbstractBaseIntegration, HealthStatus
from core.integrations.registry import ProviderRegistry


@ProviderRegistry.register("telegram")
class TelegramProvider(AbstractBaseIntegration):
    """Native Telegram Bot API Integration."""

    def validate_config(self) -> bool:
        token = self.config.get("bot_token", "")
        return bool(token and token != "YOUR_TELEGRAM_BOT_TOKEN")

    def initialize(self) -> bool:
        self.is_initialized = self.validate_config()
        return self.is_initialized

    def health_check(self) -> HealthStatus:
        if not self.validate_config():
            return HealthStatus(is_healthy=False, message="Telegram bot_token missing")

        import requests
        token = self.config.get("bot_token", "8819096503:AAEqOGM_9y7MbWTLa-5Ds5MBQfxQtiD3XKs")
        url = f"https://api.telegram.org/bot{token}/getMe"

        start = time.time()
        try:
            resp = requests.get(url, timeout=10)
            latency = (time.time() - start) * 1000
            if resp.status_code == 200 and resp.json().get("ok"):
                bot_info = resp.json().get("result", {})
                self.last_health = HealthStatus(is_healthy=True, latency_ms=latency, status_code="200", message=f"Connected as @{bot_info.get('username')}")
            else:
                self.last_health = HealthStatus(is_healthy=False, latency_ms=latency, status_code=str(resp.status_code), message=resp.text[:200])
        except Exception as e:
            self.last_health = HealthStatus(is_healthy=False, message=str(e))

        return self.last_health

    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        import requests
        token = self.config.get("bot_token", "8819096503:AAEqOGM_9y7MbWTLa-5Ds5MBQfxQtiD3XKs")
        api_base = f"https://api.telegram.org/bot{token}"

        if action in ("send_message", "send"):
            chat_id = params.get("chat_id", params.get("to", ""))
            text = params.get("text", params.get("message", ""))
            resp = requests.post(f"{api_base}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=15)
            if resp.status_code != 200:
                resp = requests.post(f"{api_base}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=15)
            resp.raise_for_status()
            return {"status": "done", "output": resp.json()}

        elif action == "status":
            resp = requests.get(f"{api_base}/getMe", timeout=10)
            resp.raise_for_status()
            return {"status": "done", "output": resp.json()}

        return {"status": "error", "error": f"Unknown action: {action}"}

    def shutdown(self) -> bool:
        self.is_initialized = False
        return True
