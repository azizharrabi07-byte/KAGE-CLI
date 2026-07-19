"""agents/builtin.py — the builtin domain agents.

Real implementations live in their own modules (whatsapp/obsidian/system/meta).
This module re-exports them and keeps the ``BUILTIN_AGENTS`` roster.
"""

from __future__ import annotations

from .meta.agent import MetaAgent
from .obsidian.agent import ObsidianAgent
from .system.agent import SystemAgent
from .whatsapp.agent import WhatsAppAgent

BUILTIN_AGENTS = [WhatsAppAgent, ObsidianAgent, SystemAgent, MetaAgent]

__all__ = ["WhatsAppAgent", "ObsidianAgent", "SystemAgent", "MetaAgent", "BUILTIN_AGENTS"]
