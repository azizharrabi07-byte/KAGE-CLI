#!/usr/bin/env python3
"""
Trilium / TriliumDroid Agent — Talks to Trilium Notes ETapi (default http://localhost:8080 or sync server).
Methods: list_notes, read_note, write_note, append_note, search
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
        self.etapi_token = ""
        self.headers = {}

    def wake(self, task_data: dict) -> dict:
        """Wake up: configure connection to Trilium ETapi."""
        global requests
        import requests as _requests
        requests = _requests

        config_path = Path(__file__).parent.parent.parent / "config.toml"
        user_config_path = Path.home() / ".kage" / "config.toml"

        config = {}
        if config_path.exists():
            config = self._load_toml(config_path)
        elif user_config_path.exists():
            config = self._load_toml(user_config_path)

        trilium_config = config.get("trilium", {})
        self.base_url = trilium_config.get("url", "http://localhost:8080").rstrip("/")
        self.etapi_token = trilium_config.get("etapi_token", "")
        self.headers = {"Accept": "application/json"}
        if self.etapi_token and self.etapi_token != "YOUR_TRILIUM_ETAPI_TOKEN":
            self.headers["Authorization"] = self.etapi_token

        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        action = task_data.get("action", "list_notes")
        note_id = task_data.get("note_id", task_data.get("id", ""))
        parent_id = task_data.get("parent_note_id", "root")
        title = task_data.get("title", "Untitled Note")
        content = task_data.get("content", "")
        query = task_data.get("query", task_data.get("search", ""))

        try:
            if action == "list_notes":
                result = self._list_notes(query)
            elif action in ("read_note", "read"):
                if not note_id:
                    return {"status": "error", "output": "Missing 'note_id' parameter"}
                result = self._read_note(note_id)
            elif action in ("write_note", "create_note", "write"):
                result = self._create_or_update_note(note_id, parent_id, title, content)
            elif action == "append_note":
                if not note_id:
                    return {"status": "error", "output": "Missing 'note_id' parameter"}
                result = self._append_note(note_id, content)
            elif action == "search":
                if not query:
                    return {"status": "error", "output": "Missing 'query' parameter"}
                result = self._search(query)
            else:
                return {"status": "error", "output": f"Unknown action: {action}"}

            return {"status": "done", "output": result}
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "output": f"Cannot connect to Trilium ETapi at {self.base_url}. Ensure Trilium / TriliumDroid or sync server is active."
            }
        except Exception as e:
            return {"status": "error", "output": str(e)}

    def _list_notes(self, search: str = "") -> Union[List[Dict], Dict]:
        url = f"{self.base_url}/etapi/notes"
        params = {"search": search} if search else {"search": "#root"}
        resp = requests.get(url, headers=self.headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _read_note(self, note_id: str) -> Dict:
        # Get metadata
        meta_resp = requests.get(f"{self.base_url}/etapi/notes/{note_id}", headers=self.headers, timeout=10)
        meta_resp.raise_for_status()
        note_meta = meta_resp.json()

        # Get content
        content_resp = requests.get(f"{self.base_url}/etapi/notes/{note_id}/content", headers=self.headers, timeout=10)
        content_resp.raise_for_status()

        note_meta["content"] = content_resp.text
        return note_meta

    def _create_or_update_note(self, note_id: str, parent_id: str, title: str, content: str) -> Dict:
        if note_id:
            # Update content
            headers = {**self.headers, "Content-Type": "text/html"}
            resp = requests.put(
                f"{self.base_url}/etapi/notes/{note_id}/content",
                headers=headers,
                data=content.encode("utf-8"),
                timeout=10,
            )
            resp.raise_for_status()
            return {"status": "updated", "noteId": note_id}
        else:
            # Create new note
            headers = {**self.headers, "Content-Type": "application/json"}
            payload = {
                "parentNoteId": parent_id or "root",
                "title": title,
                "type": "text",
                "content": content,
            }
            resp = requests.post(f"{self.base_url}/etapi/notes", headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()

    def _append_note(self, note_id: str, content_to_append: str) -> Dict:
        existing = self._read_note(note_id)
        current_content = existing.get("content", "")
        new_content = current_content + "\n<br>\n" + content_to_append
        return self._create_or_update_note(note_id=note_id, parent_id="", title="", content=new_content)

    def _search(self, query: str) -> List[Dict]:
        url = f"{self.base_url}/etapi/notes"
        resp = requests.get(url, headers=self.headers, params={"search": query}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        elif isinstance(data, list):
            return data
        return [data]

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
