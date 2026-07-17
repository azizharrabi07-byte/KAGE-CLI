#!/usr/bin/env python3
"""
ollama.py — Ollama Local Models Integration Provider.
"""

import time
from typing import Dict, Any
from core.integrations.base import AbstractBaseIntegration, HealthStatus
from core.integrations.registry import ProviderRegistry


@ProviderRegistry.register("ollama")
class OllamaProvider(AbstractBaseIntegration):
    """Native Ollama Local Integration Provider."""

    def validate_config(self) -> bool:
        return True

    def initialize(self) -> bool:
        self.is_initialized = True
        return True

    def health_check(self) -> HealthStatus:
        import requests
        base_url = self.config.get("base_url", "http://localhost:11434/v1")
        start = time.time()
        try:
            resp = requests.get(f"{base_url.rstrip('/')}/models", timeout=5)
            latency = (time.time() - start) * 1000
            if resp.status_code == 200:
                self.last_health = HealthStatus(is_healthy=True, latency_ms=latency, status_code="200", message="Ollama server active")
            else:
                self.last_health = HealthStatus(is_healthy=False, latency_ms=latency, status_code=str(resp.status_code), message=resp.text[:200])
        except Exception as e:
            self.last_health = HealthStatus(is_healthy=False, message=f"Ollama server unreachable: {e}")

        return self.last_health

    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        import requests

        base_url = self.config.get("base_url", "http://localhost:11434/v1")
        model = params.get("model") or self.config.get("model", "llama3")
        messages = params.get("messages", [])
        system = params.get("system", "")
        temperature = params.get("temperature", 0.7)

        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        resp = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Content-Type": "application/json"},
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
