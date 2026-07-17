# KAGE OS v2.1 — Personal AI Agent Operating System for Termux

A modular, high-performance, purely local terminal-based AI operating system designed for **Termux (Android)** and Linux/macOS command-line environments. Powered natively by **Google Gemini 2.5 Flash** with automated model fallbacks, Obsidian Local REST API, WhatsApp microservice bridge, phone health telemetry, and universal core OS features for **Browser-Use**, **OpenHands Sandbox**, **Awesome MCP Protocol**, and **CrewAI Orchestrator**.

---

## What's New in v2.1

1. **`kage logs` Command**: Tail or real-time stream (`kage logs -f`) the daemon supervisor log.
2. **`kage schedule list` Command**: Query and format scheduled cron jobs directly from `kage.db`.
3. **`kage test whatsapp` Command**: End-to-end bridge connection and automated ping test against configured `test_number`.
4. **Enhanced Security `.gitignore`**: Comprehensive protection for secrets (`config.toml`), WhatsApp session tokens (`auth_info/`), and SQLite databases.
5. **Standardized Script Exit Codes**: All CLI commands return exit code `0` on success or `1` on error for automation scripts.

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    KAGE OS TERMINAL FRONTEND (kage_cli.py)               │
│  kage (Interactive REPL) | kage chat | kage logs | kage schedule | kage test│
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Unix Domain Socket IPC (~/.kage/kage.sock)
┌────────────────────────────────────▼────────────────────────────────────┐
│                    SUPERVISOR DAEMON (kage.py)                          │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Shared Context (self.context)
      ┌──────────────────────────────┼──────────────────────────────┐
      │                              │                              │
┌─────▼─────────────────────┐  ┌─────▼─────────────────────┐  ┌─────▼─────────────────────┐
│  GEMINI 2.5 FLASH BRAIN   │  │   UNIVERSAL OS FEATURES   │  │   PERSONAL DOMAIN AGENTS  │
│    (core/brain.py)        │  │     (core/features/)      │  │         (agents/)         │
├───────────────────────────┤  ├───────────────────────────┤  ├───────────────────────────┤
│ • Direct Google REST API  │  │ • browser (browser-use)   │  │ • obsidian (Port 27123)   │
│ • Automated Model Failover│  │ • openhands (Code/Sandbox)│  │ • whatsapp (Port 3030)    │
│ • ReAct Reasoning Loop    │  │ • mcp (Awesome MCP)       │  │ • system (Phone Hardware) │
│                           │  │ • crew (CrewAI Teams)     │  │ • meta (Git Self-Upgrade) │
└───────────────────────────┘  └───────────────────────────┘  └───────────────────────────┘
```

---

## Installation & Termux Setup

```bash
# 1. Clone Repository
git clone https://github.com/azizharrabi07-byte/KAGE-CLI.git
cd KAGE-CLI

# 2. Run Setup Script
bash setup.sh
```

### Configuration Setup (`~/.kage/config.toml`)

```toml
[llm]
provider = "gemini"
api_key = "YOUR_GEMINI_API_KEY"
model = "gemini-2.5-flash"

[obsidian]
url = "http://localhost:27123"
api_key = "4224414d3d95d207e1058d16f30424c9"
vault = "KAGE"

[whatsapp]
test_number = "1234567890"

[mcp]
servers = [
    { name = "fetch", url = "http://localhost:8000/mcp" },
    { name = "filesystem", url = "http://localhost:8001/mcp" }
]
```

---

## CLI Command Reference

```bash
# 1. Interactive REPL Session
kage

# 2. View Daemon Supervisor Logs
kage logs                  # Show last 50 lines of kage.log
kage logs --follow         # Stream logs in real-time

# 3. Scheduled Tasks Management
kage schedule list         # List scheduled cron jobs from kage.db
kage schedule add --cron "0 9 * * *" --agent system --task '{"action":"health"}'
kage schedule delete 1

# 4. WhatsApp Bridge Verification Test
kage test whatsapp         # Verify bridge & test ping message

# 5. Direct AI Brain Prompts & Automation
kage chat "Search the web for OpenHands framework"
kage chat "Create a note in Obsidian titled Meeting.md"

# 6. System Status & Health Telemetry
kage status
kage health

# 7. Background Daemon Management
kage daemon start
kage daemon status
kage daemon stop
```

---

## Verification & Automated Test Suite

```bash
python3 -m unittest discover -s tests
```
