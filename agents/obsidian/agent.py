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
from typing import Dict, List, Optional, Union

# Lazy imports — loaded in wake()


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False
        self.base_url = ""
        self.api_key = ""
        self.headers = {}

    def wake(self, task_data: dict) -> dict:
        """Wake up: configure connection, load heavy libs."""
        global requests
        import requests as _requests
        requests = _requests

        # Load config
        config_path = Path(__file__).parent.parent.parent / "config.toml"
        user_config_path = Path.home() / ".kage" / "config.toml"

        config = {}
        if config_path.exists():
            config = self._load_toml(config_path)
        elif user_config_path.exists():
            config = self._load_toml(user_config_path)

        obs_config = config.get("obsidian", {})
        self.base_url = obs_config.get("url", "http://localhost:27123").rstrip("/")
        self.api_key = obs_config.get("api_key", "")
        self.headers = {"Accept": "application/json"}
        if self.api_key and self.api_key != "YOUR_OBSIDIAN_KEY":
            self.headers["Authorization"] = f"Bearer {self.api_key}"

        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        action = task_data.get("action", "list_files")
        vault = task_data.get("vault", "vault")
        path = task_data.get("path", "").lstrip("/")
        content = task_data.get("content", "")
        query = task_data.get("query", "")

        try:
            if action == "list_files":
                result = self._list_files(vault)
            elif action == "read_file":
                if not path:
                    return {"status": "error", "output": "Missing 'path' parameter for read_file"}
                result = self._read_file(vault, path)
            elif action == "write_file":
                if not path:
                    return {"status": "error", "output": "Missing 'path' parameter for write_file"}
                result = self._write_file(vault, path, content)
            elif action == "append":
                if not path:
                    return {"status": "error", "output": "Missing 'path' parameter for append"}
                result = self._append(vault, path, content)
            elif action == "search":
                if not query:
                    return {"status": "error", "output": "Missing 'query' parameter for search"}
                result = self._search(vault, query)
            else:
                return {"status": "error", "output": f"Unknown action: {action}"}

            return {"status": "done", "output": result}
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "output": f"Cannot connect to Obsidian REST API at {self.base_url}. Ensure Obsidian is running with Local REST API plugin enabled."
            }
        except Exception as e:
            return {"status": "error", "output": str(e)}

    def _list_files(self, vault: str) -> List[str]:
        resp = requests.get(f"{self.base_url}/vault/", headers=self.headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            return data.get("files", [])
        elif isinstance(data, list):
            return data
        return []

    def _read_file(self, vault: str, path: str) -> str:
        resp = requests.get(f"{self.base_url}/vault/{path}", headers=self.headers, timeout=10)
        resp.raise_for_status()
        try:
            data = resp.json()
            if isinstance(data, dict):
                return data.get("content", resp.text)
            return resp.text
        except (json.JSONDecodeError, ValueError):
            return resp.text

    def _write_file(self, vault: str, path: str, content: str) -> str:
        headers = {**self.headers, "Content-Type": "text/markdown"}
        resp = requests.put(
            f"{self.base_url}/vault/{path}",
            headers=headers,
            data=content.encode("utf-8"),
            timeout=10,
        )
        resp.raise_for_status()
        return f"Successfully written to {path}"

    def _append(self, vault: str, path: str, content: str) -> str:
        headers = {**self.headers, "Content-Type": "text/markdown"}
        resp = requests.post(
            f"{self.base_url}/vault/{path}",
            headers=headers,
            data=content.encode("utf-8"),
            timeout=10,
        )
        resp.raise_for_status()
        return f"Successfully appended to {path}"

    def _search(self, vault: str, query: str) -> Union[List[Dict], List[str]]:
        headers = {**self.headers, "Content-Type": "application/json"}
        resp = requests.post(
            f"{self.base_url}/search/simple/",
            headers=headers,
            json={"query": query},
            timeout=10,
        )
        if resp.status_code == 404:
            resp = requests.post(
                f"{self.base_url}/search/",
                headers=headers,
                json={"query": query},
                timeout=10,
            )
        resp.raise_for_status()
        try:
            data = resp.json()
            if isinstance(data, dict):
                return data.get("files", data.get("results", []))
            return data
        except Exception:
            return [resp.text]

    def sleep(self):
        self.alive = False
        gc.collect()

    @staticmethod
    def _load_toml(config_path: Path) -> Dict:
        """Load configuration using toml package or fallback parser."""
        try:
            import toml
            return toml.load(config_path)
        except ImportError:
            config = {}
            current_section = None
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        current_section = line[1:-1]
                        config[current_section] = {}
                    elif "=" in line and current_section:
                        key, _, val = line.partition("=")
                        config[current_section][key.strip()] = val.strip().strip('"\'')
            return config
