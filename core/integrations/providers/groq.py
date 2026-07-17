#!/usr/bin/env python3
"""
groq.py — Groq Integration Provider for KAGE OS.
High-speed OpenAI-compatible inference bridge.
"""

import time
from typing import Dict, Any
from core.integrations.base import AbstractBaseIntegration, HealthStatus
from core.integrations.registry import ProviderRegistry


@ProviderRegistry.register("groq")
class GroqProvider(AbstractBaseIntegration):
    """Native Groq API Integration Provider."""

    def validate_config(self) -> bool:
        api_key = self.config.get("api_key", "")
        return bool(api_key and api_key not in ("", "YOUR_KEY_HERE"))

    def initialize(self) -> bool:
        self.is_initialized = self.validate_config()
        return self.is_initialized

    def health_check(self) -> HealthStatus:
        if not self.validate_config():
            return HealthStatus(is_healthy=False, message="Groq API key missing")

        import requests
        api_key = self.config.get("api_key", "")
        base_url = self.config.get("base_url", "https://api.groq.com/openai/v1")
        url = f"{base_url.rstrip('/')}/models"

        start = time.time()
        try:
            resp = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            latency = (time.time() - start) * 1000
            if resp.status_code == 200:
                self.last_health = HealthStatus(is_healthy=True, latency_ms=latency, status_code="200", message="Groq operational")
            else:
                self.last_health = HealthStatus(is_healthy=False, latency_ms=latency, status_code=str(resp.status_code), message=resp.text[:200])
        except Exception as e:
            self.last_health = HealthStatus(is_healthy=False, message=str(e))

        return self.last_health

    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        import requests

        api_key = self.config.get("api_key", "")
        base_url = self.config.get("base_url", "https://api.groq.com/openai/v1")
        model = params.get("model") or self.config.get("model", "llama-3.3-70b-versatile")
        messages = params.get("messages", [])
        system = params.get("system", "")
        temperature = params.get("temperature", 0.7)

        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        resp = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": full_messages, "temperature": temperature},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]["message"]
        return {
            "status": "done",
            "role": choice.get("role", "assistant"),
            "content": choice.get("content", ""),
            "model": data.get("model", model)
        }

    def shutdown(self) -> bool:
        self.is_initialized = False
        return True
