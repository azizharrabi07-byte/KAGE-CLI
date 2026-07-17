#!/usr/bin/env python3
"""
wizard.py — Interactive System Configuration Wizard for KAGE OS.
Guides user step-by-step through configuring LLM keys, Obsidian tokens, Telegram tokens, and MCP options.
Part of Phase 6 Production CLI Engine.
"""

from pathlib import Path
from typing import Dict, Any
from kage_cli import set_config_key, _load_config


class ConfigWizard:
    """Interactive CLI wizard for step-by-step KAGE configuration."""

    @staticmethod
    def run_interactive_setup() -> bool:
        print("\n┌─── KAGE OS INTERACTIVE CONFIGURATION WIZARD ───┐")
        print("Set up your AI provider and personal integrations.\n")

        # 1. LLM Provider Setup
        print("1. Select LLM Provider:")
        print("   [1] Google Gemini (Recommended — Low Latency)")
        print("   [2] Groq (Ultra Fast Llama 3.3)")
        print("   [3] OpenRouter (Multi-model router)")
        print("   [4] Ollama (Local offline models)")

        p_choice = input("Select provider [1-4] (default 1): ").strip()
        p_map = {"1": "gemini", "2": "groq", "3": "openrouter", "4": "ollama"}
        provider = p_map.get(p_choice, "gemini")
        set_config_key("llm.provider", provider)

        if provider in ("gemini", "groq", "openrouter"):
            key = input(f"Enter API Key for {provider.upper()}: ").strip()
            if key:
                set_config_key("llm.api_key", key)

        # 2. Obsidian Local REST API Setup
        print("\n2. Configure Obsidian Local REST API:")
        obs_token = input("Enter Obsidian REST API token (default 4224414d3d95d207e1058d16f30424c9): ").strip()
        if obs_token:
            set_config_key("obsidian.api_key", obs_token)

        # 3. Telegram Bot Setup
        print("\n3. Configure Telegram Bot Integration:")
        tg_token = input("Enter Telegram Bot Token (@Mini_kage_bot): ").strip()
        if tg_token:
            set_config_key("telegram.bot_token", tg_token)

        print("\n✅ Setup Complete! Config saved to ~/.kage/config.toml")
        print("Start the background daemon with: 'kage daemon start'")
        return True
