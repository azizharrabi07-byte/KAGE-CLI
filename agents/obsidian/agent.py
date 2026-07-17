#!/usr/bin/env python3
"""
Obsidian Agent — Talks to Obsidian Local REST API (default localhost:27123).
Methods: list_files, read_file, write_file, append, search
"""

import gc
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Lazy imports — loaded only in wake()


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False
        self.base_url = ""
        self.api_key = ""
        self.headers = {}

    def wake(self, task_data: dict) -> dict:
        """Wake up: configure connection, load heavy libs."""
        # Lazy import
        global requests
        import requests as _requests
        requests = _requests

        # Load config
        config_path = Path(__file__).parent.parent.parent / "config.toml"
        try:
            import toml
            config = toml.load(config_path)
        except ImportError:
            config = self._manual_parse(config_path)

        obs_config = config.get("obsidian", {})
        self.base_url = obs_config.get("url", "http://localhost:27123").rstrip("/")
        self.api_key = obs_config.get("api_key", "")
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        action = task_data.get("action", "list_files")
        vault = task_data.get("vault, "vault")
        path = task_data.get("path", "")
        content = task_data.get("content", "")
        query = task_data.get("query", "")

        try:
            if action == "list_files":
                result = self._list_files(vault)
            elif action == "read_file":
                result = self._read_file(vault, path)
            elif action == "write_file":
                result = self._write_file(vault, path, content)
            elif action == "append":
                result = self._append(vault, path, content)
            elif action == "search":
                result = self._search(vault, query)
            else:
                return {"status": "error", "output": f"Unknown action: {action}"}

            return {"status": "done", "output": result}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "output": f"Cannot connect to Obsidian at {self.base_url}"}
        except Exception as e:
            return {"status": "error", "output": str(e)}

    def _list_files(self, vault: str) -> List[str]:
        resp = requests.get(f"{self.base_url}/vault/", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("files", [])

    def _read_file(self, vault: str, path: str) -> str:
        resp = requests.get(f"{self.base_url}/vault/{path}", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("content", "")

    def _write_file(self, vault: str, path: str, content: str) -> str:
        resp = requests.put(
            f"{self.base_url}/vault/{path}",
            headers={**self.headers, "Content-Type": "text/markdown"},
            data=content,
            timeout=10,
        )
        resp.raise_for_status()
        return f"Written to {path}"

    def _append(self, vault: str, path: str, content: str) -> str:
        resp = requests.patch(
            f"{self.base_url}/vault/{path}",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"content": content},
            timeout=10,
        )
        resp.raise_for_status()
        return f"Appended to {path}"

    def _search(self, vault: str, query: str) -> List[Dict]:
        resp = requests.post(
            f"{self.base_url}/search/",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"query": query},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("files", [])

    def sleep(self):
        self.alive = False
        # Unload requests
        for mod in list(sys.modules.keys()):
            if mod.startswith("requests"):
                del sys.modules[mod]
        gc.collect()

    @staticmethod
    def _manual_parse(config_path: Path) -> Dict:
        """Fallback config parser when toml isn't installed."""
        config = {}
        current_section = None
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("["):
                    current_section = line[1:-1]
                    config[current_section] = {}
                elif "=" in line and current_section:
                    key, _, val = line.partition("=")
                    config[current_section][key.strip()] = val.strip().strip('"')
        return config
