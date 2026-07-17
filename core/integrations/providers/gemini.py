#!/usr/bin/env python3
"""
gemini.py — Google Gemini Integration Provider for KAGE OS.
Supports direct REST calls to Google Generative Language API with automated model failover.
"""

import time
from typing import Dict, Any
from core.integrations.base import AbstractBaseIntegration, HealthStatus
from core.integrations.registry import ProviderRegistry


@ProviderRegistry.register("gemini")
class GeminiProvider(AbstractBaseIntegration):
    """Native Google Gemini API Integration with Health Checks & Rate Limits."""

    def validate_config(self) -> bool:
        api_key = self.config.get("api_key", "")
        return bool(api_key and api_key not in ("YOUR_KEY_HERE", "YOUR_GEMINI_API_KEY_HERE"))

    def initialize(self) -> bool:
        self.is_initialized = self.validate_config()
        return self.is_initialized

    def health_check(self) -> HealthStatus:
        if not self.validate_config():
            return HealthStatus(is_healthy=False, message="Gemini API key missing or unconfigured")

        import requests
        api_key = self.config.get("api_key", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

        start = time.time()
        try:
            resp = requests.get(url, timeout=10)
            latency = (time.time() - start) * 1000
            if resp.status_code == 200:
                self.last_health = HealthStatus(is_healthy=True, latency_ms=latency, status_code="200", message="Gemini API operational")
            else:
                self.last_health = HealthStatus(is_healthy=False, latency_ms=latency, status_code=str(resp.status_code), message=resp.text[:200])
        except Exception as e:
            self.last_health = HealthStatus(is_healthy=False, message=str(e))

        return self.last_health

    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        import requests

        api_key = self.config.get("api_key", "")
        primary_model = params.get("model") or self.config.get("model", "gemini-2.5-flash")
        messages = params.get("messages", [])
        system = params.get("system", "")
        temperature = params.get("temperature", 0.7)

        fallback_models = [primary_model, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
        seen = set()
        models_to_try = [m for m in fallback_models if not (m in seen or seen.add(m))]

        last_err = ""
        for current_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key}"
            contents = []
            for m in messages:
                role = "model" if m.get("role") in ("assistant", "model") else "user"
                contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})

            payload = {
                "contents": contents,
                "generationConfig": {"temperature": temperature}
            }
            if system:
                payload["systemInstruction"] = {"parts": [{"text": system}]}

            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    return {"status": "done", "role": "assistant", "content": text, "model": current_model}

            last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            if resp.status_code in (503, 429):
                time.sleep(1)
                continue
            else:
                break

        return {"status": "error", "error": last_err or "Gemini generation failed"}

    def shutdown(self) -> bool:
        self.is_initialized = False
        return True
