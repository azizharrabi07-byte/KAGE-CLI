# KAGE OS Phase 3 — Interactive REPL & Dynamic Config Engine

A modular, high-performance local terminal-based AI operating system designed for **Termux (Android)** and Linux/macOS command-line environments. Phase 3 brings OpenCode-style interactive REPL shell with up-arrow history, slash commands (`/models`, `/providers`, `/config`), and live dynamic LLM switching across **Gemini**, **Groq**, **OpenRouter**, and **Ollama**.

---

## What's New in Phase 3

1. **Interactive REPL (`KAGE> ` Prompt)**:
   - Launch by running `kage` or `kage interactive`.
   - Up-arrow command history powered by Python's built-in `readline` (saved in `~/.kage/history`).
2. **Slash Commands System**:
   - `/help`: List all interactive commands.
   - `/models`: Discover supported models for active provider (or `/models --all`).
   - `/providers`: View active and standby LLM providers (`gemini`, `groq`, `openrouter`, `ollama`).
   - `/config list`: Inspect full configuration with masked API keys.
   - `/config get <key>`: View value for key e.g. `/config get llm.model`.
   - `/config set <key> <val>`: Live update TOML configuration e.g. `/config set llm.provider groq`.
3. **Dynamic LLM Engine Reload**:
   - `core/brain.py` reloads `config.toml` dynamically on every request. Live provider switching without restarting daemons!
4. **Enhanced Error Recovery & ANSI Styling**:
   - High-contrast ANSI colors for status, warnings, and errors.
   - Human-readable 429 rate limit notifications with suggested provider switching commands.

---

## Supported LLM Providers & Model Discovery

| Provider | Base URL | Featured Models |
| :--- | :--- | :--- |
| **`gemini`** | `https://generativelanguage.googleapis.com` | `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-2.0-flash-lite` |
| **`groq`** | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`, `gemma-2-9b-it` |
| **`openrouter`** | `https://openrouter.ai/api/v1` | `anthropic/claude-3.5-sonnet`, `google/gemini-2.5-flash`, `mistralai/mistral-7b-instruct` |
| **`ollama`** | `http://localhost:11434/v1` | Local models dynamically discovered via `ollama list` |

---

## Interactive REPL Shell Example

```text
┌──────────────────────────────────────────────────────────────┐
│  ███▄▄▄▄   ▄████████  ▄████████    ▄████████  ▄██████▄       │
│  ███▀▀▀██▄ ███    ███ ███    ███   ███    ███ ███    ███     │
│  ███   ███ ███    █▀  ███    █▀    ███    █▀  ███    █▀      │
│  ███   ███ ███       ▄███▄▄▄      ▄███▄▄▄     ███    ███     │
│  ███   ███ ███      ▀▀███▀▀▀     ▀▀███▀▀▀     ███    ███     │
│  ███   ███ ███    █▄  ███    █▄    ███    █▄  ███    █▄      │
│  ███   ███ ███    ███ ███    ███   ███    ███ ███    ███     │
│   ▀█   █▀  ████████▀  ██████████   ██████████  ▀██████▀      │
│                                                              │
│  KAGE OS Phase 3 • OpenCode Terminal Shell for Termux        │
│  Type /help for slash commands or enter prompt to chat.      │
└──────────────────────────────────────────────────────────────┘

KAGE> /providers

┌─── CONFIGURED PROVIDERS ───┐
  • gemini       [ACTIVE]   (3 models)
  • groq         [STANDBY]  (4 models)
  • openrouter   [STANDBY]  (4 models)
  • ollama       [STANDBY]  (4 models)
└─────────────────────────────┘

KAGE> /config set llm.provider groq
✓ Successfully set llm.provider = "groq"
ℹ Provider switched to 'groq'. Brain will reload dynamically on next call.

KAGE> Search the web for OpenHands framework
> {"action": "browser", "task": {"action": "search", "query": "OpenHands framework"}}

[EXECUTION OUTPUT]
[
  {
    "title": "www.openhands.dev",
    "url": "https://www.openhands.dev/",
    "snippet": "Meet OpenHands, the open-source platform for cloud coding agents..."
  }
]
```

---

## Verification & Automated Test Suite

Run unit and integration test suite:

```bash
python3 -m unittest discover -s tests
```
