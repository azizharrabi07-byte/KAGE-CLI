"""core/plugins.py — plugin discovery & registration (KAGE v2).

Agents are installable plugins. A plugin is a directory containing a
``manifest.yaml`` plus optional ``system_prompt.md``, ``agent.py``, ``workflow.py``,
``tools.py``, ``tests/`` and ``docs/``. KAGE scans a plugin root and registers
every valid plugin, importing its agent class lazily (started on demand).

``manifest.yaml`` (minimal):
    name: security-agent
    version: 1.0.0
    agent_class: SecurityAgent      # class in agent.py
    description: Audits code & deps for vulnerabilities
    emoji: 🛡️
    tools: [search.web, filesystem.read]
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("kage.plugins")


@dataclass
class PluginManifest:
    name: str
    version: str = "0.0.0"
    agent_class: str = ""
    description: str = ""
    emoji: str = "🧩"
    tools: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "version": self.version, "agent_class": self.agent_class,
                "description": self.description, "emoji": self.emoji, "tools": list(self.tools),
                "keywords": list(self.keywords), "path": self.path}


def _parse_yaml(text: str) -> Dict[str, Any]:
    """Tiny YAML-subset parser (key: value, lists with ``-``) — no dependency."""
    out: Dict[str, Any] = {}
    current_list: Optional[str] = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if re.match(r"^\s*-\s+", line):
            val = re.sub(r"^\s*-\s+", "", line).strip().strip('"\'')
            if current_list is not None:
                out[current_list].append(val)
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"\'')
            current_list = None
            if val == "":
                out[key] = []
                current_list = key
            else:
                out[key] = val
    return out


def load_manifest(plugin_dir: Path) -> Optional[PluginManifest]:
    manifest_path = plugin_dir / "manifest.yaml"
    if not manifest_path.exists():
        return None
    data = _parse_yaml(manifest_path.read_text(encoding="utf-8"))
    if not data.get("name"):
        return None
    return PluginManifest(
        name=str(data["name"]),
        version=str(data.get("version", "0.0.0")),
        agent_class=str(data.get("agent_class", "")),
        description=str(data.get("description", "")),
        emoji=str(data.get("emoji", "🧩"))[:4] or "🧩",
        tools=list(data.get("tools", [])) if isinstance(data.get("tools"), list) else [],
        keywords=list(data.get("keywords", [])) if isinstance(data.get("keywords"), list) else [],
        path=str(plugin_dir),
    )


class PluginManager:
    """Discovers plugins under a root and registers their agents into a registry."""

    def __init__(self, registry: Any = None, plugin_root: str = "kage/plugins") -> None:
        self.registry = registry
        self.plugin_root = Path(plugin_root)
        self.installed: Dict[str, PluginManifest] = {}

    def discover(self) -> List[PluginManifest]:
        found: List[PluginManifest] = []
        if not self.plugin_root.exists():
            return found
        for child in sorted(self.plugin_root.iterdir()):
            if not child.is_dir():
                continue
            manifest = load_manifest(child)
            if manifest:
                found.append(manifest)
        return found

    def install_all(self) -> int:
        n = 0
        for manifest in self.discover():
            self.installed[manifest.name] = manifest
            if self.registry is not None:
                self._register(manifest)
            n += 1
        log.info("installed %d plugin(s)", n)
        return n

    def install(self, name: str) -> bool:
        manifest = load_manifest(self.plugin_root / name)
        if manifest is None:
            return False
        self.installed[name] = manifest
        if self.registry is not None:
            self._register(manifest)
        return True

    def remove(self, name: str) -> bool:
        if name not in self.installed:
            return False
        del self.installed[name]
        if self.registry is not None and name in getattr(self.registry, "list", lambda: [])():
            try:
                self.registry._factories.pop(name, None)
                self.registry._instances.pop(name, None)
            except Exception:  # noqa: BLE001
                pass
        return True

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self.installed.values()]

    def _register(self, manifest: PluginManifest) -> None:
        """Lazy-register the plugin agent. Imports only when first used."""
        if not manifest.agent_class:
            return
        dotted = f"{manifest.path.replace('/', '.')}.agent".lstrip(".")
        try:
            import importlib
            module = importlib.import_module(dotted)
        except Exception as exc:  # noqa: BLE001
            log.warning("plugin %s agent import failed: %s", manifest.name, exc)
            return
        cls = getattr(module, manifest.agent_class, None)
        if cls is not None and self.registry is not None:
            self.registry.register(cls, config={"_plugin": manifest.name,
                                                "description": manifest.description,
                                                "emoji": manifest.emoji})
