#!/usr/bin/env python3
"""
obsidian.py — Obsidian Local REST API Integration Provider.
Communicates with local Obsidian instance on port 27123.
"""

import time
from typing import Dict, Any
from core.integrations.base import AbstractBaseIntegration, HealthStatus
from core.integrations.registry import ProviderRegistry


@ProviderRegistry.register("obsidian")
class ObsidianProvider(AbstractBaseIntegration):
    """Native Obsidian Local REST API Integration Provider."""

    def validate_config(self) -> bool:
        url = self.config.get("url", "http://localhost:27123")
        return bool(url)

    def initialize(self) -> bool:
        self.is_initialized = True
        return True

    def health_check(self) -> HealthStatus:
        import requests
        base_url = self.config.get("url", "http://localhost:27123").rstrip("/")
        api_key = self.config.get("api_key", "4224414d3d95d207e1058d16f30424c9")
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

        start = time.time()
        try:
            resp = requests.get(f"{base_url}/vault/", headers=headers, timeout=5)
            latency = (time.time() - start) * 1000
            if resp.status_code in (200, 204):
                self.last_health = HealthStatus(is_healthy=True, latency_ms=latency, status_code="200", message="Obsidian Local REST API active")
            else:
                self.last_health = HealthStatus(is_healthy=False, latency_ms=latency, status_code=str(resp.status_code), message=resp.text[:200])
        except Exception as e:
            self.last_health = HealthStatus(is_healthy=False, message=f"Obsidian offline: {e}")

        return self.last_health

    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        import requests
        base_url = self.config.get("url", "http://localhost:27123").rstrip("/")
        api_key = self.config.get("api_key", "4224414d3d95d207e1058d16f30424c9")
        vault = self.config.get("vault", "KAGE")
        path = params.get("path", "").strip().lstrip("/")
        content = params.get("content", "")
        query = params.get("query", "")

        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

        if action == "list_files":
            resp = requests.get(f"{base_url}/vault/", headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            files = data.get("files", []) if isinstance(data, dict) else data
            return {"status": "done", "output": files, "vault": vault}

        elif action == "read_file":
            resp = requests.get(f"{base_url}/vault/{path}", headers=headers, timeout=10)
            resp.raise_for_status()
            return {"status": "done", "output": resp.text, "path": path}

        elif action == "write_file":
            h = {**headers, "Content-Type": "text/markdown"}
            resp = requests.put(f"{base_url}/vault/{path}", headers=h, data=content.encode("utf-8"), timeout=10)
            resp.raise_for_status()
            return {"status": "done", "output": f"Successfully written to {path}", "vault": vault}

        elif action == "append":
            h = {**headers, "Content-Type": "text/markdown"}
            resp = requests.post(f"{base_url}/vault/{path}", headers=h, data=content.encode("utf-8"), timeout=10)
            resp.raise_for_status()
            return {"status": "done", "output": f"Successfully appended to {path}", "vault": vault}

        elif action == "search":
            h = {**headers, "Content-Type": "application/json"}
            resp = requests.post(f"{base_url}/search/simple/", headers=h, json={"query": query}, timeout=10)
            resp.raise_for_status()
            return {"status": "done", "output": resp.json()}

        return {"status": "error", "error": f"Unknown action: {action}"}

    def shutdown(self) -> bool:
        self.is_initialized = False
        return True
