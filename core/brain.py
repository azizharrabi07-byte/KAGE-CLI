#!/usr/bin/env python3
"""
brain.py — LLM wrapper. Routes messages to OpenRouter/OpenAI-compatible APIs.
All imports lazy — loaded when call_llm() is invoked.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


def _load_config() -> Dict:
    """Load config.toml — lazy import toml or fallback parser."""
    config_paths = [
        Path(__file__).parent.parent / "config.toml",
        Path.home() / ".kage" / "config.toml",
    ]
    
    config_path = None
    for p in config_paths:
        if p.exists():
            config_path = p
            break

    if not config_path:
        return {}

    try:
        import toml
        return toml.load(config_path)
    except ImportError:
        config = {}
        current_section = None
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1]
                    config[current_section] = {}
                elif "=" in line and current_section:
                    key, _, val = line.partition("=")
                    config[current_section][key.strip()] = val.strip().strip('"\'')
        return config


def extract_action_json(content: str) -> Optional[Dict[str, Any]]:
    """Extract and parse agent action JSON block from LLM output."""
    if not content or "action" not in content:
        return None

    # First, try code block extraction
    code_block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", content)
    if code_block_match:
        try:
            data = json.loads(code_block_match.group(1))
            if isinstance(data, dict) and "action" in data:
                return data
        except json.JSONDecodeError:
            pass

    # Balanced bracket matcher for nested JSON
    def find_json_objects(text: str) -> List[str]:
        objs = []
        stack = []
        start_idx = -1
        in_string = False
        escape = False

        for i, char in enumerate(text):
            if char == '"' and not escape:
                in_string = not in_string
            elif not in_string:
                if char == '{':
                    if not stack:
                        start_idx = i
                    stack.append('{')
                elif char == '}':
                    if stack:
                        stack.pop()
                        if not stack:
                            objs.append(text[start_idx:i+1])
            escape = (char == '\\' and not escape)
        return objs

    possible_json = find_json_objects(content)
    for json_str in possible_json:
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "action" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue

    return None


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
        last_msg = messages[-1]["content"] if messages else "no input"
        return {
            "role": "assistant",
            "content": f"[ECHO MODE — no API key configured] Received: {last_msg}",
            "model": "echo",
        }

    import requests

    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
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
            "role": choice.get("role", "assistant"),
            "content": choice.get("content", ""),
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
- Send WhatsApp messages (action: "whatsapp", task: {"action": "send", "to": "...", "text": "..."})
- Read/write Obsidian notes (action: "obsidian", task: {"action": "read_file"|"write_file"|"list_files", "path": "..."})
- Check phone health (action: "system", task: {})
- Upgrade yourself (action: "meta", task: {"action": "check"|"pull"})

When the user asks you to execute an action, respond with a JSON action block:
{"action": "<agent_name>", "task": {<task_data>}}

If no agent is needed, just respond normally.
Available agents: whatsapp, obsidian, system, meta

Keep responses short and direct. You are efficient — no unnecessary words.
"""
