#!/usr/bin/env python3
"""
brain.py — Dynamic LLM Router supporting Google Gemini, Groq, OpenRouter, and Ollama.
Reloads config dynamically on every call to support live provider and model switching.
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Provider model directory
PROVIDER_MODELS = {
    "gemini": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"],
    "groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma-2-9b-it", "llama3-70b-8192"],
    "openrouter": ["anthropic/claude-3.5-sonnet", "google/gemini-2.5-flash", "mistralai/mistral-7b-instruct", "meta-llama/llama-3.3-70b-instruct"],
    "ollama": ["llama3", "mistral", "qwen2.5", "phi3"]
}


def _load_config() -> Dict:
    """Reload config dynamically on every request from local config.toml and ~/.kage/config.toml."""
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
    """Call active provider LLM (Gemini, Groq, OpenRouter, or Ollama) with dynamic config loading."""
    config = _load_config()
    llm_config = config.get("llm", {})

    provider = (os.environ.get("LLM_PROVIDER") or llm_config.get("provider", "gemini")).lower()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY") or os.environ.get("OPENROUTER_API_KEY") or llm_config.get("api_key", "")
    primary_model = os.environ.get("LLM_MODEL") or llm_config.get("model", "")
    base_url = os.environ.get("LLM_BASE_URL") or llm_config.get("base_url", "")

    if not primary_model:
        primary_model = PROVIDER_MODELS.get(provider, ["gemini-2.5-flash"])[0]

    if not api_key and provider != "ollama" and api_key in ("", "YOUR_KEY_HERE", "YOUR_GEMINI_API_KEY_HERE"):
        last_msg = messages[-1]["content"] if messages else "no input"
        return {
            "role": "assistant",
            "content": f"[ECHO MODE — no valid API key configured for provider '{provider}'] Received: {last_msg}",
            "model": "echo",
        }

    import requests

    # 1. Google Gemini Provider
    if provider in ("gemini", "google"):
        fallback_models = [primary_model, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
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
                    "generationConfig": {"temperature": temperature}
                }

                if system:
                    payload["systemInstruction"] = {"parts": [{"text": system}]}

                resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=60)

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return {"role": "assistant", "content": text, "model": current_model}

                if resp.status_code == 429:
                    last_err = f"⚠️ Gemini rate limit exceeded (429) on model '{current_model}'. Suggest switching provider e.g. '/config set llm.provider groq'."
                    time.sleep(1)
                    continue

                err_data = resp.json() if resp.headers.get("content-type") == "application/json" else {}
                err_msg = err_data.get("error", {}).get("message", resp.text)
                last_err = f"[Gemini Error {resp.status_code} on {current_model}: {err_msg}]"

            except Exception as e:
                last_err = str(e)
                time.sleep(1)
                continue

        return {"role": "assistant", "content": last_err or "[Gemini request failed]", "model": primary_model, "error": last_err}

    # 2. Groq Provider
    elif provider == "groq":
        endpoint = base_url or "https://api.groq.com/openai/v1"
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        try:
            resp = requests.post(
                f"{endpoint.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": primary_model, "messages": full_messages, "temperature": temperature},
                timeout=60,
            )
            if resp.status_code == 429:
                return {
                    "role": "assistant",
                    "content": f"⚠️ Groq rate limit exceeded (429) on model '{primary_model}'. Try switching model e.g. '/config set llm.model llama-3.3-70b-versatile' or waiting.",
                    "model": primary_model,
                    "error": "rate_limit",
                }
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]["message"]
            return {"role": choice.get("role", "assistant"), "content": choice.get("content", ""), "model": data.get("model", primary_model)}
        except Exception as e:
            return {"role": "assistant", "content": f"[Groq LLM Error: {e}]", "model": primary_model, "error": str(e)}

    # 3. Ollama Local Provider
    elif provider == "ollama":
        endpoint = base_url or "http://localhost:11434/v1"
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        try:
            resp = requests.post(
                f"{endpoint.rstrip('/')}/chat/completions",
                headers={"Content-Type": "application/json"},
                json={"model": primary_model, "messages": full_messages, "temperature": temperature},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]["message"]
            return {"role": choice.get("role", "assistant"), "content": choice.get("content", ""), "model": data.get("model", primary_model)}
        except requests.exceptions.ConnectionError:
            return {
                "role": "assistant",
                "content": f"⚠️ Cannot connect to Ollama service at {endpoint}. Ensure Ollama is running ('ollama serve').",
                "model": primary_model,
                "error": "connection_error",
            }
        except Exception as e:
            return {"role": "assistant", "content": f"[Ollama LLM Error: {e}]", "model": primary_model, "error": str(e)}

    # 4. OpenRouter Provider
    else:
        endpoint = base_url or "https://openrouter.ai/api/v1"
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        try:
            resp = requests.post(
                f"{endpoint.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": primary_model, "messages": full_messages, "temperature": temperature},
                timeout=60,
            )
            if resp.status_code == 429:
                return {
                    "role": "assistant",
                    "content": f"⚠️ OpenRouter rate limit exceeded (429) on model '{primary_model}'. Switch provider or check quota.",
                    "model": primary_model,
                    "error": "rate_limit",
                }
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]["message"]
            return {"role": choice.get("role", "assistant"), "content": choice.get("content", ""), "model": data.get("model", primary_model)}
        except Exception as e:
            return {"role": "assistant", "content": f"[LLM Error: {e}]", "model": primary_model, "error": str(e)}


KAGE_SYSTEM_PROMPT = """You are Kage — a unified personal AI operating system running on the user's phone.
You have native access to core OS features AND domain agents:

CORE FEATURES:
- browser: Web search and live webpage scraping (action: "browser", task: {"action": "search"|"fetch", "query": "...", "url": "..."})
- openhands: Sandboxed bash command execution, Python snippet evaluation, and workspace file writing (action: "openhands", task: {"action": "execute_cmd"|"run_python"|"write_code", "command": "...", "code": "..."})
- mcp: Connect to local/remote Model Context Protocol tool servers (action: "mcp", task: {"action": "list_servers"|"call_tool", "server": "...", "tool": "...", "args": {}})
- crew: Multi-role AI agent crew orchestration (action: "crew", task: {"action": "run_crew", "template": "...", "topic": "..."})

DOMAIN AGENTS:
- whatsapp: Send/read WhatsApp messages (action: "whatsapp", task: {"action": "send"|"read", "to": "...", "text": "..."})
- telegram: Send/read Telegram bot messages (action: "telegram", task: {"action": "send_message"|"status", "chat_id": "...", "text": "..."})
- obsidian: Read/write Obsidian notes via Local REST API (action: "obsidian", task: {"action": "read_file"|"write_file"|"list_files"|"search", "path": "...", "content": "..."})
- system: Check phone health, battery, storage, CPU (action: "system", task: {})
- meta: Self-upgrade via git pull (action: "meta", task: {"action": "check"|"pull"})

To trigger any feature or agent action, emit a single JSON action block:
{"action": "<feature_or_agent_name>", "task": {<task_data>}}

Keep responses short and direct. You are efficient and helpful.
"""

class brain:
    def __init__(self):
        pass
    def ask(self, prompt: str) -> str:
        from .brain import call_llm, KAGE_SYSTEM_PROMPT
        messages = [{"role": "user", "content": prompt}]
        result = call_llm(messages, system=KAGE_SYSTEM_PROMPT)
        return result.get("content", "")

# Also create an alias for uppercase (if needed)
Brain = brain

class brain:
    def __init__(self):
        pass
    def ask(self, prompt: str) -> str:
        # call_llm and KAGE_SYSTEM_PROMPT are already defined in this module
        messages = [{"role": "user", "content": prompt}]
        result = call_llm(messages, system=KAGE_SYSTEM_PROMPT)
        return result.get("content", "")

Brain = brain
