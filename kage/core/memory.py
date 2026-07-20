"""core/memory.py — long-term per-user memory.

Two storage formats, mirroring the Hermes/arena-handoff foundation:
  * JSON  — fast key/value lookup (the hot path)
  * Markdown — human-readable export (the "second brain")

Memory is keyed by transport user id. In production swap this for SQLite.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class MemoryStore:
    def __init__(self, root: str = ".kage/memory") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.json_path = self.root / "memory.json"
        self.md_dir = self.root / "notes"
        self.md_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict[str, str]] = self._load()
        self._attributions: Dict[str, Dict[str, str]] = self._load_attr()

    def _load(self) -> Dict[str, Dict[str, str]]:
        if self.json_path.exists():
            try:
                return json.loads(self.json_path.read_text() or "{}")
            except json.JSONDecodeError:
                return {}
        return {}

    def _save(self) -> None:
        self.json_path.write_text(json.dumps(self._cache, indent=2, ensure_ascii=False))

    def _attr_path(self) -> Path:
        return self.root / "attribution.json"

    def _load_attr(self) -> Dict[str, Dict[str, str]]:
        p = self._attr_path()
        if p.exists():
            try:
                return json.loads(p.read_text() or "{}")
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_attr(self) -> None:
        self._attr_path().write_text(json.dumps(self._attributions, indent=2, ensure_ascii=False))

    def _user(self, user_id: str) -> Dict[str, str]:
        return self._cache.setdefault(str(user_id), {})

    # -- API -----------------------------------------------------------------
    def get(self, user_id: str) -> Dict[str, str]:
        return dict(self._user(user_id))

    def set(self, user_id: str, key: str, value: str) -> None:
        self._user(user_id)[key] = value
        self._save()

    def forget(self, user_id: str, key: str) -> bool:
        store = self._user(user_id)
        if key in store:
            del store[key]
            attrs = self._attributions.setdefault(str(user_id), {})
            attrs.pop(key, None)
            self._save_attr()
            self._save()
            return True
        return False

    def set_attribution(self, user_id: str, key: str, agent: str) -> None:
        """Record which agent stored a key."""
        self._attributions.setdefault(str(user_id), {})[key] = agent
        self._save_attr()

    def get_attribution(self, user_id: str, key: str) -> str:
        """Return the agent name that stored a key, or '' if unknown."""
        return self._attributions.get(str(user_id), {}).get(key, "")

    def attributed_get(self, user_id: str) -> Dict[str, Dict[str, str]]:
        """Return {key: {'value': v, 'agent': agent}} for rich recall."""
        store = dict(self._user(user_id))
        attrs = self._attributions.get(str(user_id), {})
        return {k: {"value": v, "agent": attrs.get(k, "Kage")} for k, v in store.items()}

    def all_users(self) -> list[str]:
        return sorted(self._cache)

    # -- markdown export -----------------------------------------------------
    def export_markdown(self, user_id: str) -> Path:
        """Write the user's memory to a readable Markdown note."""
        store = self._user(user_id)
        safe = "".join(c if c.isalnum() else "_" for c in str(user_id)) or "user"
        path = self.md_dir / f"{safe}.md"
        lines = [f"# Memory for {user_id}", ""]
        for k, v in store.items():
            lines += [f"## {k}", "", v, ""]
        path.write_text("\n".join(lines))
        return path
