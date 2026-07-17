# KAGE OS — Personal AI Agent Operating System for Termux

A modular, high-performance, purely local terminal-based AI operating system designed for **Termux (Android)** and Linux/macOS command-line environments. Inspired by OpenCode and OpenClaude, KAGE OS runs natively in your terminal with zero web server dependencies, powered by **Google Gemini 2.5 Flash** and integrated with native capabilities for web browsing, code execution sandboxing, Model Context Protocol (MCP) server bridging, CrewAI multi-agent orchestration, Obsidian note taking, WhatsApp messaging, and phone hardware telemetry.

---

## Key Highlights & Architectural Overview

### 1. Gemini 2.5 Flash LLM Brain & Automated Failover
* **Native Integration**: Directly targets Google Generative Language REST API with low latency.
* **Smart Failover Pipeline**: Automatically fails over across models (`gemini-2.5-flash` $\rightarrow$ `gemini-2.0-flash` $\rightarrow$ `gemini-2.0-flash-lite`) if rate limits or high-demand quota errors occur.
* **Autonomous ReAct Loop**: Automatically executes tool calls and feeds observations back into the LLM brain to complete multi-step tasks in a single prompt.

### 2. Universal Built-in Core Features (`core/features/`)
Core capabilities built directly into the operating system and shared natively across every personal domain agent:
* **`browser` (browser-use)**: Live DuckDuckGo web search, URL fetching, link extraction, and clean readable text scraping.
* **`openhands` (OpenHands)**: Sandboxed terminal shell command execution, inline Python evaluation, and workspace file writing.
* **`mcp` (Awesome MCP)**: Model Context Protocol client engine connecting Kage to remote or local MCP tool servers.
* **`crew` (CrewAI)**: Multi-role AI agent crew orchestrator for coordinating sequential team workflows (e.g. Researcher $\rightarrow$ Writer, Developer $\rightarrow$ Reviewer).

### 3. Personal Domain Agents (`agents/`)
* **`obsidian`**: Deep integration with Obsidian Local REST API (`http://localhost:27123`) to read, write, append, and search notes in vault `KAGE`.
* **`whatsapp`**: Background Baileys Node.js microservice (`http://localhost:3030`) for sending/reading WhatsApp messages with JID auto-formatting.
* **`system`**: Real-time phone telemetry monitoring battery level, storage space, CPU load, and system uptime via Termux API and Linux kernel sysfs.
* **`meta`**: Self-upgrade engine running automated `git pull` updates and unittest execution.

### 4. OpenCode-Style Pure Terminal Interface
* **Zero Web/Host Dependency**: Runs 100% locally inside your Termux terminal without launching web servers or local websites.
* **Interactive Terminal REPL**: Launch an interactive shell with `kage` or `kage interactive` featuring monochrome ASCII banners, prompt history, and slash commands (`/status`, `/health`, `/agents`, `/traces`, `/schedules`).
* **Unix Socket Daemon IPC**: Background supervisor process listens at `~/.kage/kage.sock` for instant command dispatch.

---

## Directory Structure

```text
KAGE-CLI/
├── kage.py                 # Background Supervisor Daemon & IPC Socket Server
├── kage_cli.py             # OpenCode Terminal Frontend & Interactive REPL
├── config.toml             # System & API Configuration
├── setup.sh                # One-Click Installer for Termux & Linux
├── core/
│   ├── brain.py            # Gemini 2.5 Flash API Wrapper & ReAct Parser
│   ├── memory.py           # SQLite Persistent DB (traces, workflows, cron)
│   ├── permissions.py      # Safety & Auto-Approval Permission Model
│   ├── scheduler.py        # Background Cron Job Engine
│   └── features/           # Universal OS Capabilities
│       ├── browser.py      # browser-use Web Search & Scraper
│       ├── openhands.py    # OpenHands Code & Sandbox Execution Engine
│       ├── mcp.py          # Awesome MCP Client Bridge
│       └── crew.py         # CrewAI Multi-Agent Team Orchestrator
├── agents/                 # Personal Domain Agents
│   ├── obsidian/           # Obsidian Notes Agent
│   ├── whatsapp/           # WhatsApp Messaging Agent
│   ├── system/             # Phone Telemetry Agent
│   └── meta/               # Self-Upgrade Agent
└── tests/                  # Automated Integration & Unit Test Suite
```

---

## Installation & Setup on Termux

```bash
# 1. Clone Repository
git clone https://github.com/azizharrabi07-byte/KAGE-CLI.git
cd KAGE-CLI

# 2. Run Setup Script
bash setup.sh
```

### Configuration Setup (`~/.kage/config.toml`)

Edit your configuration file at `~/.kage/config.toml`:

```toml
[llm]
provider = "gemini"
api_key = "YOUR_GEMINI_API_KEY"
model = "gemini-2.5-flash"

[obsidian]
url = "http://localhost:27123"
api_key = "4224414d3d95d207e1058d16f30424c9"
vault = "KAGE"

[mcp]
servers = [
    { name = "fetch", url = "http://localhost:8000/mcp" },
    { name = "filesystem", url = "http://localhost:8001/mcp" }
]
```

---

## Usage Guide

### 1. Launch Interactive Terminal REPL Shell

To start the continuous interactive session in Termux:

```bash
kage
```

**Interactive Slash Commands**:
* `/help` — Display list of slash commands
* `/status` — View active system state and IPC socket
* `/health` — Inspect battery %, disk usage, CPU, uptime
* `/agents` — List registered domain agents
* `/traces` — Show recent execution trace logs
* `/schedules` — List active cron tasks
* `/clear` — Clear terminal screen
* `/exit` — Quit interactive session

### 2. Direct CLI Commands

```bash
# Chat & Execute Multi-Step Actions
kage chat "Search the web for OpenHands AI and summarize it"
kage chat "Create a note in Obsidian titled Standup.md with content Sprint meeting completed"
kage chat "Run Python code: import math; print(math.factorial(10))"

# Inspect System Health & State
kage status
kage health

# Manage Domain Personal Agents
kage agent list
kage agent wake obsidian --task '{"action":"list_files"}'
kage agent wake whatsapp --task '{"action":"status"}'

# Cron Scheduler
kage schedule add --cron "0 9 * * *" --agent system --task '{"action":"health"}'
kage schedule list

# Background Daemon Management
kage daemon start
kage daemon status
kage daemon stop
```

---

## Verification & Unit Testing

To run the full suite of automated unit and integration tests:

```bash
python3 -m unittest discover -s tests
```
