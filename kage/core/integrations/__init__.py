"""core/integrations — unified abstractions for external services."""

from __future__ import annotations

from .base import Integration
from .base_integration import BaseIntegration
from .obsidian import ObsidianIntegration
from .whatsapp import WhatsAppIntegration

__all__ = [
    "Integration",
    "BaseIntegration",
    "ObsidianIntegration",
    "WhatsAppIntegration",
]
