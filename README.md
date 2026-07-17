# KAGE OS — Persistent User Memory & Full Integration Suite

A modular, high-performance local terminal-based AI operating system designed for **Termux (Android)** and Linux/macOS command-line environments. Powered natively by **Google Gemini 2.5 Flash** with automated model fallbacks, **Per-User Persistent Memory** (`~/.kage/memory.json`), Telegram Bot integration (@Mini_kage_bot), Obsidian Local REST API, WhatsApp microservice bridge, phone health telemetry, and universal core OS features for **Browser-Use**, **OpenHands Sandbox**, **Awesome MCP Protocol**, and **CrewAI Orchestrator**.

---

## What's New in Brain & Memory Suite

### 1. Persistent Memory per User (`~/.kage/memory.json`)
* **Keyed by `user_id`**: Automatically tracks facts, names, preferences, and custom attributes for every user (e.g. Telegram chat ID or local CLI user).
* **Automatic Recall**: When a user says *"My name is Alex"* or *"Remember that I like Python"*, Kage updates `~/.kage/memory.json` and immediately recalls saved context on future turns.
* **Storage Schema**:
  ```json
  {
    "12345678": {
      "name": "Alex",
      "facts": ["Likes Python and Termux", "Located in Tunis"],
      "kv": {"favorite_language": "Python"},
      "last_updated": "2026-07-17T11:49:37"
    }
  }
  ```

### 2. Integration-Aware System Prompt
Updated `KAGE_SYSTEM_PROMPT` in `core/brain.py` with explicit action definitions:
- `system` — Check phone health, battery, storage, CPU telemetry.
- `openhands` — Execute sandboxed bash commands, evaluate Python scripts, synthesize workspace files.
- `crew` — Multi-role sequential AI agent crew orchestration.
- `obsidian` — Read/write notes in Obsidian vault via Local REST API (port 27123).
- `whatsapp` — Send/read WhatsApp messages over Baileys bridge (port 3030).
- `telegram` — Dispatch Telegram bot messages (@Mini_kage_bot).
- `browser` — Live web search & web page scraping.
- `mcp` — Call tool endpoints on remote/local Model Context Protocol servers.
- `memory` — Store user details, facts, or preferences to persistent memory.

Mandatory action execution block standard:
```json
{"action": "<action_name>", "task": {<task_data>}}
```

---

## Quick Start & Commands

```bash
# 1. Start Supervisor Daemon (spawns Telegram bot polling worker automatically)
kage daemon start

# 2. Check Telegram Bot Status
kage telegram status

# 3. Interactive Terminal Shell
kage
```

---

## Verification & Automated Unit Testing

```bash
python3 -m unittest discover -s tests
```
