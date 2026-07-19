"""agents/builtin.py — placeholder domain agents (Phase 1).

These are intentionally lightweight scaffolds that satisfy the wake/execute/
sleep lifecycle so the supervisor can route to them. Each is a clear seam to
fill in with real integrations later. Telegram/Discord live in their own
modules because they bring third-party dependencies.
"""

from __future__ import annotations

from typing import Any, Dict

from ..core.base_agent import BaseAgent


class WhatsAppAgent(BaseAgent):
    """WhatsApp <-> Kage bridge. Forwards inbound messages, replies on request."""

    name = "whatsapp"
    kind = "whatsapp"
    description = "Bridges WhatsApp messages to/from Kage."
    emoji = "💬"

    def wake(self) -> None:
        # TODO: connect WhatsApp Business API / Baileys bridge.
        self._awake = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True, "agent": self.name, "note": "WhatsApp bridge not configured."}

    def sleep(self) -> None:
        self._awake = False


class ObsidianAgent(BaseAgent):
    """Reads/writes notes to an Obsidian vault and links ideas."""

    name = "obsidian"
    kind = "obsidian"
    description = "Manages your Obsidian vault (notes, links)."
    emoji = "📓"

    def wake(self) -> None:
        self.vault = self.config.get("vault_path", "~/Documents/Obsidian")
        self._awake = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True, "agent": self.name, "vault": str(self.vault),
                "note": "Vault ops to be implemented."}

    def sleep(self) -> None:
        self._awake = False


class SystemAgent(BaseAgent):
    """Host health, uptime, service management (Sentinel)."""

    name = "system"
    kind = "system"
    description = "Reports host health and manages background services."
    emoji = "🛡️"

    def wake(self) -> None:
        import os, platform
        self._awake = True
        self._host = platform.node() or "termux"

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        import os
        return {"ok": True, "agent": self.name, "host": getattr(self, "_host", "unknown"),
                "loadavg": getattr(os, "getloadavg", lambda: [0])[0]}

    def sleep(self) -> None:
        self._awake = False


class MetaAgent(BaseAgent):
    """Self-reflection / meta-agent: reasons about the crew and routes."""

    name = "meta"
    kind = "meta"
    description = "Meta-agent: reflects on crew state and suggests routing."
    emoji = "🪞"

    def wake(self) -> None:
        self._awake = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        agents = []
        if self.supervisor is not None:
            agents = self.supervisor.registry.list()
        return {"ok": True, "agent": self.name, "known_agents": agents}

    def sleep(self) -> None:
        self._awake = False


# Convenience: the full placeholder roster for the registry.
BUILTIN_AGENTS = [WhatsAppAgent, ObsidianAgent, SystemAgent, MetaAgent]
