"""
Providers Package for KAGE OS.
Auto-registers all core integration providers upon import.
"""

from .gemini import GeminiProvider
from .groq import GroqProvider
from .openrouter import OpenRouterProvider
from .ollama import OllamaProvider
from .obsidian import ObsidianProvider
from .whatsapp import WhatsAppProvider
from .telegram import TelegramProvider

__all__ = [
    "GeminiProvider",
    "GroqProvider",
    "OpenRouterProvider",
    "OllamaProvider",
    "ObsidianProvider",
    "WhatsAppProvider",
    "TelegramProvider",
]
