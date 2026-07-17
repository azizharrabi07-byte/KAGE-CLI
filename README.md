# KAGE OS — Telegram Bot Integration & Personal AI Operating System

A modular, high-performance local terminal-based AI operating system designed for **Termux (Android)** and Linux/macOS command-line environments. Powered natively by **Google Gemini 2.5 Flash** with automated model fallbacks, Telegram Bot remote access (@Mini_kage_bot), Obsidian Local REST API, WhatsApp microservice bridge, phone health telemetry, and universal core OS features for **Browser-Use**, **OpenHands Sandbox**, **Awesome MCP Protocol**, and **CrewAI Orchestrator**.

---

## Telegram Bot Integration (@Mini_kage_bot)

KAGE OS features native long-polling integration with Telegram, allowing remote control of your phone and AI system from any device via Telegram messages.

* **Bot Token Configuration**: Saved in `~/.kage/config.toml` under `[telegram]` (`8819096503:AAEqOGM_9y7MbWTLa-5Ds5MBQfxQtiD3XKs`).
* **Interactive Bot Commands**:
  * `/start` / `/help` — Welcome guide and command index.
  * `/status` — Live system overview and active IPC socket state.
  * `/health` — Real-time phone telemetry (battery %, storage, CPU load, uptime).
  * `/agents` — List registered personal domain agents.
  * *Natural Language Prompts* — Direct query to Gemini 2.5 Flash brain with multi-step tool execution.
* **Auto-Start Daemon Spawning**:
  * Whenever `kage daemon start` or `kage.py` initializes, KAGE supervisor automatically spawns the background Telegram bot polling daemon (tracked via `~/.kage/telegram.pid`).

### Telegram CLI Management Commands

```bash
kage telegram start     # Start Telegram bot long-polling process in background
kage telegram status    # Check if @Mini_kage_bot daemon process is running
kage telegram stop     # Terminate Telegram bot background daemon
```

---

## System Architecture

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                    KAGE OS TERMINAL FRONTEND (kage_cli.py)                │
│  kage (REPL) | kage chat | kage telegram | kage schedule | kage status    │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ Unix Domain Socket IPC (~/.kage/kage.sock)
┌────────────────────────────────────▼──────────────────────────────────────┐
│                    SUPERVISOR DAEMON (kage.py)                            │
│  Auto-Spawns Background Telegram Polling Worker (@Mini_kage_bot)          │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ Shared Context (self.context)
      ┌──────────────────────────────┼──────────────────────────────┐
      │                              │                              │
┌─────▼─────────────────────┐  ┌─────▼─────────────────────┐  ┌─────▼─────────────────────┐
│  GEMINI 2.5 FLASH BRAIN   │  │   UNIVERSAL OS FEATURES   │  │   PERSONAL DOMAIN AGENTS  │
│    (core/brain.py)        │  │     (core/features/)      │  │         (agents/)         │
├───────────────────────────┤  ├───────────────────────────┤  ├───────────────────────────┤
│ • Direct Google REST API  │  │ • browser (browser-use)   │  │ • telegram (@Mini_kage)   │
│ • Automated Model Failover│  │ • openhands (Code/Sandbox)│  │ • obsidian (Port 27123)   │
│ • ReAct Reasoning Loop    │  │ • mcp (Awesome MCP)       │  │ • whatsapp (Port 3030)    │
│                           │  │ • crew (CrewAI Teams)     │  │ • system (Phone Telemetry)│
└───────────────────────────┘  └───────────────────────────┘  └───────────────────────────┘
```

---

## Quick Start Guide for Termux

```bash
# 1. Start Background Supervisor & Telegram Bot
kage daemon start

# 2. Check Telegram Bot Status
kage telegram status

# 3. Enter OpenCode Terminal Interactive Shell
kage
```

---

## Verification & Automated Test Suite

```bash
python3 -m unittest discover -s tests
```
