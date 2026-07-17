#!/usr/bin/env python3
"""
whatsapp.py — WhatsApp Baileys Microservice Bridge Integration Provider.
"""

import time
from typing import Dict, Any
from core.integrations.base import AbstractBaseIntegration, HealthStatus
from core.integrations.registry import ProviderRegistry


@ProviderRegistry.register("whatsapp")
class WhatsAppProvider(AbstractBaseIntegration):
    """Native WhatsApp Baileys Microservice Integration."""

    def validate_config(self) -> bool:
        return True

    def initialize(self) -> bool:
        self.is_initialized = True
        return True

    def health_check(self) -> HealthStatus:
        import requests
        bridge_url = self.config.get("url", "http://localhost:3030").rstrip("/")
        start = time.time()
        try:
            resp = requests.get(f"{bridge_url}/health", timeout=3)
            latency = (time.time() - start) * 1000
            if resp.status_code == 200:
                data = resp.json()
                self.last_health = HealthStatus(is_healthy=True, latency_ms=latency, status_code="200", message=f"WhatsApp connection: {data.get('whatsapp')}")
            else:
                self.last_health = HealthStatus(is_healthy=False, latency_ms=latency, status_code=str(resp.status_code), message=resp.text[:200])
        except Exception as e:
            self.last_health = HealthStatus(is_healthy=False, message=f"WhatsApp bridge offline: {e}")

        return self.last_health

    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        import requests
        bridge_url = self.config.get("url", "http://localhost:3030").rstrip("/")

        if action == "status":
            resp = requests.get(f"{bridge_url}/status", timeout=5)
            return {"status": "done", "output": resp.json()}

        elif action == "send":
            to = params.get("to", "")
            text = params.get("text", "")
            resp = requests.post(f"{bridge_url}/send", json={"to": to, "text": text}, timeout=15)
            return {"status": "done", "output": resp.json()}

        elif action == "read":
            resp = requests.get(f"{bridge_url}/read", timeout=10)
            return {"status": "done", "output": resp.json()}

        return {"status": "error", "error": f"Unknown action: {action}"}

    def shutdown(self) -> bool:
        self.is_initialized = False
        return True
