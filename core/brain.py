#!/usr/bin/env python3
"""
brain.py — LLM wrapper with support for Google Gemini API and OpenRouter/OpenAI compatible APIs.
Includes automated fallback models for Gemini (2.5-flash -> 2.0-flash -> 2.0-flash-lite) and multi-turn message formatting.
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


def _load_config() -> Dict:
    """Load config.toml — user config (~/.kage/config.toml) overrides repo config."""
    config_paths = [
        Path(__file__).parent.parent / "config.toml",
        Path.home() / ".kage" / "config.toml",
    ]

    merged_config = {}
    for p in config_paths:
        if not p.exists():
            continue
        try:
            import toml
            data = toml.load(p)
        except ImportError:
            data = {}
            current_section = None
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        current_section = line[1:-1]
                        if current_section not in data:
                            data[current_section] = {}
                    elif "=" in line and current_section:
                        key, _, val = line.partition("=")
                        data[current_section][key.strip()] = val.strip().strip('"\'')

        for sec, items in data.items():
            if sec not in merged_config:
                merged_config[sec] = {}
            if isinstance(items, dict):
                merged_config[sec].update(items)

    return merged_config


def extract_action_json(content: str) -> Optional[Dict[str, Any]]:
    """Extract and parse feature or agent action JSON block from LLM output."""
    if not content or "action" not in content:
        return None

    code_block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", content)
    if code_block_match:
        try:
            data = json.loads(code_block_match.group(1))
            if isinstance(data, dict) and "action" in data:
                return data
        except json.JSONDecodeError:
            pass

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
    """Call the LLM (Gemini with fallback or OpenRouter) and return response."""
    config = _load_config()
    llm_config = config.get("llm", {})

    provider = os.environ.get("LLM_PROVIDER") or llm_config.get("provider", "gemini").lower()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENROUTER_API_KEY") or llm_config.get("api_key", "")
    primary_model = os.environ.get("LLM_MODEL") or llm_config.get("model", "gemini-2.5-flash")
    base_url = os.environ.get("LLM_BASE_URL") or llm_config.get("base_url", "https://openrouter.ai/api/v1")

    if not api_key or api_key in ("YOUR_KEY_HERE", "YOUR_GEMINI_API_KEY_HERE"):
        last_msg = messages[-1]["content"] if messages else "no input"
        return {
            "role": "assistant",
            "content": f"[ECHO MODE — no valid API key configured] Received: {last_msg}",
            "model": "echo",
        }

    import requests

    # 1. Direct Gemini API Integration with Fallback Models
    if provider in ("gemini", "google") or "gemini" in primary_model.lower():
        fallback_models = [primary_model, "gemini-2.0-flash", "gemini-2.0-flash-lite"]
        seen = set()
        models_to_try = [m for m in fallback_models if not (m in seen or seen.add(m))]

        last_err = ""
        for current_model in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key}"
                contents = []
                for m in messages:
                    role = "model" if m.get("role") in ("assistant", "model") else "user"
                    contents.append({
                        "role": role,
                        "parts": [{"text": m.get("content", "")}]
                    })

                payload = {
                    "contents": contents,
                    "generationConfig": {
                        "temperature": temperature,
                    }
                }

                if system:
                    payload["systemInstruction"] = {
                        "parts": [{"text": system}]
                    }

                resp = requests.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=60,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return {
                            "role": "assistant",
                            "content": text,
                            "model": current_model,
                        }

                err_data = resp.json() if resp.headers.get("content-type") == "application/json" else {}
                err_msg = err_data.get("error", {}).get("message", resp.text)
                last_err = f"[Gemini Error {resp.status_code} on {current_model}: {err_msg}]"

                # If 503 or 429, wait briefly and try next model fallback
                if resp.status_code in (503, 429):
                    time.sleep(1)
                    continue
                else:
                    break

            except Exception as e:
                last_err = str(e)
                time.sleep(1)
                continue

        return {
            "role": "assistant",
            "content": last_err or "[Gemini API failed on all model fallbacks]",
            "model": primary_model,
            "error": last_err,
        }

    # 2. OpenRouter / OpenAI-Compatible API Fallback
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
                "model": primary_model,
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
            "model": data.get("model", primary_model),
        }
    except Exception as e:
        return {
            "role": "assistant",
            "content": f"[LLM Error: {e}]",
            "model": primary_model,
            "error": str(e),
        }


KAGE_SYSTEM_PROMPT = """You are Kage — a unified personal AI operating system running on the user's phone.
You have native access to core OS features AND domain agents:

CORE FEATURES:
- browser: Web search and live webpage scraping (action: "browser", task: {"action": "search"|"fetch", "query": "...", "url": "..."})
- openhands: Sandboxed bash command execution, Python snippet evaluation, and workspace file writing (action: "openhands", task: {"action": "execute_cmd"|"run_python"|"write_code", "command": "...", "code": "..."})
- mcp: Connect to local/remote Model Context Protocol tool servers (action: "mcp", task: {"action": "list_servers"|"call_tool", "server": "...", "tool": "...", "args": {}})
- crew: Multi-role AI agent crew orchestration (action: "crew", task: {"action": "run_crew", "template": "...", "topic": "..."})

DOMAIN AGENTS:
- whatsapp: Send/read WhatsApp messages (action: "whatsapp", task: {"action": "send"|"read", "to": "...", "text": "..."})
- trilium: Read/write Trilium Notes (action: "trilium", task: {"action": "read_note"|"write_note"|"list_notes", "title": "...", "content": "..."})
- system: Check phone health, battery, storage, CPU (action: "system", task: {})
- meta: Self-upgrade via git pull (action: "meta", task: {"action": "check"|"pull"})

To trigger any feature or agent action, emit a single JSON action block:
{"action": "<feature_or_agent_name>", "task": {<task_data>}}

Keep responses short and direct. You are efficient and helpful.
"""
