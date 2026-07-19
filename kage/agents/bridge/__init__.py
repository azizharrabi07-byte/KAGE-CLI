"""Bridge agents — integrate external AI systems without duplicating them."""
from __future__ import annotations
from .base import BridgeAgent
from .opencode import OpenCodeBridgeAgent
from .openclaw import OpenClawBridgeAgent
__all__ = ["BridgeAgent", "OpenCodeBridgeAgent", "OpenClawBridgeAgent"]
