"""core/base_agent.py — the agent lifecycle interface.

Every agent (Telegram, Discord, WhatsApp, Obsidian, System, Meta, …)
implements the same minimal lifecycle so the supervisor can manage them
uniformly:

    wake()    — connect / prepare resources (lazy, on-demand)
    execute() — do one unit of work (blocking or async-friendly)
    sleep()   — release resources

The supervisor NEVER talks to the outside world directly; it delegates to
agents/tools. Agents are thin transport/domain layers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AgentCapability:
    """Declares what an agent can do, so the supervisor can route to it."""

    tools: list[str] = field(default_factory=list)
    """Tool names this agent owns (e.g. ["web.search", "web.fetch"])."""

    keywords: list[str] = field(default_factory=list)
    """Wake words / intents this agent handles (e.g. ["search", "news"])."""


class BaseAgent(ABC):
    """Abstract agent. Subclasses set ``name``/``kind`` and implement lifecycle."""

    #: stable identifier used by the registry
    name: str = "base"
    #: domain/transport family: discord | telegram | whatsapp | obsidian | system | meta
    kind: str = "base"
    #: one-line human description
    description: str = ""
    #: emoji used in CLI/transport output
    emoji: str = "🤖"

    def __init__(self, supervisor: Any = None, config: Optional[Dict[str, Any]] = None) -> None:
        self.supervisor = supervisor
        self.config: Dict[str, Any] = config or {}
        self._awake = False
        self.capability = AgentCapability()

    # -- lifecycle -----------------------------------------------------------
    @abstractmethod
    def wake(self) -> None:
        """Connect / prepare. Idempotent: safe to call more than once."""

    @abstractmethod
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run one task and return a structured result dict."""

    @abstractmethod
    def sleep(self) -> None:
        """Release resources. Idempotent."""

    # -- helpers -------------------------------------------------------------
    @property
    def is_awake(self) -> bool:
        return self._awake

    def info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "description": self.description,
            "emoji": self.emoji,
            "awake": self._awake,
            "tools": list(self.capability.tools),
            "keywords": list(self.capability.keywords),
        }
