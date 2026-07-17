#!/usr/bin/env python3
"""
brain.py — LLM wrapper. Routes messages to OpenRouter/OpenAI-compatible APIs.
All imports lazy — only loaded when call_llm() is invoked.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional


def _load_config() -> Dict:
    """Load config.toml — lazy import toml only when needed."""
    config_path = Path(__file__).parent.parent / "config.toml"
    if not config_path.exists():
        return {}
    try:
        import toml
        return toml.load(config_path)
    except ImportError:
        # Fallback: manual parse
        config = {}
        current_section = None
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("["):
                    current_section = line[1:-1]
                    config[current_section] = {}
                elif "=" in line and current_section:
                    key, _, val = line.partition("=")
                    config[current_section][key.strip()] = val.strip().strip('"')
        return config


def call_llm(messages: List[Dict], system: str = "", temperature: float = 0.7) -> Dict:
    """Call the LLM and return the response.

    Args:
        messages: [{"role": "user", "content": "..."}]
        system: System prompt prepended to messages
        temperature: Creativity (0-1)

    Returns:
        {"role": "assistant", "content": "...", "model": "..."}
    """
    config = _load_config()
    llm_config = config.get("llm", {})

    api_key = os.environ.get("OPENROUTER_API_KEY") or llm_config.get("api_key", "")
    base_url = os.environ.get("OPENROUTER_BASE_URL") or llm_config.get("base_url", "https://openrouter.ai/api/v1")
    model = os.environ.get("OPENROUTER_MODEL") or llm_config.get("model", "anthropic/claude-3.5-sonnet")

    if not api_key or api_key == "YOUR_KEY_HERE":
        # Fallback: echo mode for testing without API key
        last_msg = messages[-1]["content"] if messages else "no input"
        return {
            "role": "assistant",
            "content": f"[ECHO MODE — no API key configured] Received: {last_msg}",
            "model": "echo",
        }

    # Lazy import — only when actually calling the API
    import requests

    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": full_messages,
                "temperature": temperature,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]["message"]
        return {
            "role": choice["role"],
            "content": choice["content"],
            "model": data.get("model", model),
        }
    except Exception as e:
        return {
            "role": "assistant",
            "content": f"[LLM Error: {e}]",
            "model": model,
            "error": str(e),
        }


KAGE_SYSTEM_PROMPT = """You are Kage — a personal AI assistant running on the user's phone.
You have access to agents that can:
- Send WhatsApp messages
- Read/write Obsidian notes
- Check phone health (battery, storage)
- Upgrade yourself

When the user asks you to do something, respond with a JSON action block:
{"action": "<agent_name>", "task": {<task_data>}}

If no agent is needed, just respond normally.
Available agents: whatsapp, obsidian, system, meta

Keep responses short and direct. You are efficient — no unnecessary words.
"""
