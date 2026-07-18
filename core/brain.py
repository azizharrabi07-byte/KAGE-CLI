"""
core/brain.py
LLM wrapper with Hermes-style layered prompt system.
"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

# ── Configuration ──────────────────────────────────────────
# Repo root = parent of this file's package (kage-os/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

KAGE_DIR = Path.home() / ".kage"
MEMORIES_DIR = KAGE_DIR / "memories"
AGENTS_FILE = PROJECT_ROOT / "AGENTS.md"

SOUL_FILE = KAGE_DIR / "SOUL.md"
MEMORY_FILE = MEMORIES_DIR / "MEMORY.md"
USER_FILE = MEMORIES_DIR / "USER.md"
CORE_MEMORY_FILE = KAGE_DIR / "core_memory.json"

# Ensure directories exist
KAGE_DIR.mkdir(parents=True, exist_ok=True)
MEMORIES_DIR.mkdir(parents=True, exist_ok=True)

# ── Default Content Generators ─────────────────────────────

def get_default_soul() -> str:
    return """# KAGE OS — System Soul

You are KAGE, a decisive CLI-based AI operating system for Termux.
Your purpose is to act, not to plan. You MUST use your tools to take action — do not describe what you would do or plan to do without actually doing it.

## Core Rules
1. Tool Enforcement: You MUST output valid JSON action blocks. Never ask for permission before acting.
2. Decisiveness: Make decisions confidently. If uncertain, act with your best judgment and note it.
3. Memory: Use memory tools to persist important facts about the user.
4. Browser: Use browser action for any web query. depth=1 for quick answers, depth=3 for deep research.
5. Session: Maintain context across messages. Reference previous conversation when relevant.
6. Output Format: Always respond with a single JSON action block. Multiple actions are forbidden.

## Golden Rule
"You MUST use your tools to take action — do not describe what you would do or plan to do without actually doing it."
"""


def get_default_agents() -> str:
    return """# KAGE OS — Agent Instructions

## Available Agents
- browser: Web search and page fetching. Args: {"action": "browser", "query": "..."} or {"action": "browser", "url": "...", "depth": 1}
- memory: Long-term memory management. Args: {"action": "memory", "sub_action": "add|replace|remove", "content": "..."}
- core_memory: Read/write core user identity. Args: {"action": "core_memory", "sub_action": "read|write", "key": "...", "value": "..."}
- session: Session management. Args: {"action": "session", "sub_action": "new|resume|list"}
- openhands: Code execution environment.
- crew: Multi-agent task delegation.

## File Paths
- Config: ~/.kage/
- Memories: ~/.kage/memories/
- Agent definitions: AGENTS.md (project root)
- Core memory: ~/.kage/core_memory.json
- Sessions: ~/.kage/sessions.db
"""


def get_default_memory() -> str:
    return """# KAGE OS — Agent Memory

## Important Facts
- KAGE was created as a CLI AI OS for Termux.
- KAGE uses layered prompts inspired by Hermes, OpenCode, and OpenClaw.
- The golden rule enforces tool use over planning.
"""


def get_default_user() -> str:
    return """# KAGE OS — User Profile

## User Information
- No personal information stored yet.
- Use memory add to populate this file.
"""


# ── File Helpers ─────────────────────────────────────────────

def ensure_file(path: Path, default_content: str) -> str:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(default_content, encoding="utf-8")
    return path.read_text(encoding="utf-8")


# ── Core Memory ────────────────────────────────────────────

def load_core_memory() -> Dict[str, Any]:
    if CORE_MEMORY_FILE.exists():
        try:
            return json.loads(CORE_MEMORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def save_core_memory(data: Dict[str, Any]) -> None:
    CORE_MEMORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Prompt Assembly ─────────────────────────────────────────

def assemble_prompt(session_context: str = "", user_message: str = "") -> str:
    soul = ensure_file(SOUL_FILE, get_default_soul())
    agents = ensure_file(AGENTS_FILE, get_default_agents())
    memory = ensure_file(MEMORY_FILE, get_default_memory())
    user_profile = ensure_file(USER_FILE, get_default_user())
    core_mem = load_core_memory()
    core_mem_str = json.dumps(core_mem, indent=2, ensure_ascii=False) if core_mem else "{}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    parts = [
        "# === TIER 1: SOUL (STABLE) ===",
        soul,
        "",
        "# === TIER 2: AGENTS (CONTEXT) ===",
        agents,
        "",
        "# === TIER 3: MEMORY (VOLATILE) ===",
        memory,
        "",
        "# === TIER 3: USER PROFILE (VOLATILE) ===",
        user_profile,
        "",
        "# === DYNAMIC: TIMESTAMP ===",
        f"Current time: {timestamp}",
        "",
        "# === DYNAMIC: CORE MEMORY ===",
        core_mem_str,
    ]

    if session_context:
        parts.extend(["", "# === DYNAMIC: SESSION CONTEXT ===", session_context])

    parts.extend([
        "",
        "# === USER MESSAGE ===",
        user_message,
        "",
        "# === INSTRUCTION ===",
        "Respond with a SINGLE valid JSON action block. Do not output multiple actions. Do not ask for permission. ACT NOW.",
    ])

    return "\n\n".join(parts)


# ── LLM Wrapper ──────────────────────────────────────────────

class Brain:
    """LLM wrapper with layered prompt system."""

    def __init__(self, provider: str = "groq", api_key: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv(f"{self.provider.upper()}_API_KEY")
        self.model = model or self._default_model()

    def _default_model(self) -> str:
        defaults = {
            "groq": "llama-3.3-70b-versatile",
            "gemini": "gemini-1.5-pro",
            "openrouter": "anthropic/claude-3.5-sonnet",
        }
        return defaults.get(self.provider, "llama-3.3-70b-versatile")

    def _build_messages(self, user_message: str, session_context: str = "") -> List[Dict]:
        system_prompt = assemble_prompt(session_context, "")
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

    def think(self, user_message: str, session_context: str = "") -> str:
        messages = self._build_messages(user_message, session_context)

        if self.provider == "groq":
            return self._call_groq(messages)
        elif self.provider == "gemini":
            return self._call_gemini(messages)
        elif self.provider == "openrouter":
            return self._call_openrouter(messages)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _call_groq(self, messages: List[Dict]) -> str:
        import requests
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "messages": messages, "temperature": 0.3, "max_tokens": 4096},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_gemini(self, messages: List[Dict]) -> str:
        import requests
        contents = []
        system_parts = []
        for m in messages:
            if m["role"] == "system":
                system_parts.append(m["content"])
            else:
                prefix = "\n\n".join(system_parts)
                text = (prefix + "\n\n" + m["content"]) if prefix else m["content"]
                contents.append({"role": "user", "parts": [{"text": text}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        resp = requests.post(
            url,
            params={"key": self.api_key},
            json={"contents": contents, "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096}},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_openrouter(self, messages: List[Dict]) -> str:
        import requests
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://kage-os.local",
                "X-Title": "KAGE OS",
            },
            json={"model": self.model, "messages": messages, "temperature": 0.3, "max_tokens": 4096},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


# ── Post-Processing ──────────────────────────────────────────

def extract_single_action(raw: str) -> str:
    # Remove markdown code fences
    cleaned = re.sub(r"```json\s*", "", raw)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()

    # Find all JSON objects
    json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    matches = re.findall(json_pattern, cleaned, re.DOTALL)

    if not matches:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            matches = [cleaned[start:end + 1]]
        else:
            return json.dumps({"action": "reply", "message": cleaned})

    first_json = matches[0]

    try:
        parsed = json.loads(first_json)
        return json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        fixed = first_json.replace("\\'", "'")
        fixed = re.sub(r",\s*}", "}", fixed)
        fixed = re.sub(r",\s*]", "]", fixed)
        try:
            parsed = json.loads(fixed)
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            return json.dumps({"action": "reply", "message": cleaned})


# ── Convenience Function ─────────────────────────────────────

def call_llm(user_message: str, provider: str = "groq", session_context: str = "") -> str:
    brain = Brain(provider=provider)
    raw = brain.think(user_message, session_context)
    return extract_single_action(raw)


if __name__ == "__main__":
    prompt = assemble_prompt("Session: test-123", "Hello Kage!")
    print("=== ASSEMBLED PROMPT ===")
    print(prompt[:2000])
    print("\n... (truncated)")
