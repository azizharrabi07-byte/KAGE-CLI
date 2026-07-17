# KAGE OS — Personal AI Operating System

A modular, high-performance CLI & Web-based AI operating system for your phone (Termux/Android), Linux, and macOS. Powered natively by Google Gemini 2.5 Flash, connected to Obsidian Local REST API, WhatsApp, phone health telemetry, and equipped with built-in **Browser-Use**, **OpenHands Sandbox**, **MCP Engine**, and **CrewAI Orchestrator** features.

## Obsidian Local REST API Connection

Obsidian connects natively via the Local REST API plugin:
- **Default REST URL**: `http://localhost:27123`
- **Default Token**: `4224414d3d95d207e1058d16f30424c9`
- **Default Vault**: `KAGE`

Configured in `~/.kage/config.toml`:
```toml
[obsidian]
url = "http://localhost:27123"
api_key = "4224414d3d95d207e1058d16f30424c9"
vault = "KAGE"
```

## System Architecture

- **`agents/`** (Domain Personal Agents)
  - `obsidian`: Read, write, append, search notes via Obsidian Local REST API on `localhost:27123`.
  - `whatsapp`: Baileys microservice bridge (`localhost:3030`) for WhatsApp messaging.
  - `system`: Cross-platform phone telemetry (battery, storage, CPU load, uptime).
  - `meta`: Self-upgrade agent (`git pull`, test suite verification).
- **`core/features/`** (Universal Core Capabilities)
  - `browser.py` (`BrowserFeature`): Live DuckDuckGo web search, URL fetching, link parsing, and readable article scraping.
  - `openhands.py` (`OpenHandsFeature`): Sandboxed shell command execution, inline Python evaluation, and workspace file synthesis.
  - `mcp.py` (`MCPFeature`): Model Context Protocol engine connecting Kage to remote or local MCP tool servers.
  - `crew.py` (`CrewFeature`): Multi-role sequential agent team task orchestrator.
- **`core/`**
  - `brain.py`: Native **Google Gemini API** (`gemini-2.5-flash`) brain with automated JSON action extraction and automated model failover.
  - `memory.py`: SQLite WAL database (`kage.db`).
  - `permissions.py`: Safety permission engine.
  - `scheduler.py`: Background cron task scheduler.
  - `web_ui.py`: OpenCode-style HTTP Web Dashboard server (`localhost:8080`).
- **`web/`**: OpenCode-style black & white terminal landing page (`index.html`).

## Quick Start & Usage

### 1. Web Dashboard Landing Page
Launch the interactive OpenCode terminal web UI:
```bash
kage web --port 8080
```
Open **`http://localhost:8080`** in your browser!

### 2. Obsidian Notes Usage via Kage Chat
```bash
kage chat "List all files in my Obsidian vault"
kage chat "Create a new note in Obsidian titled Daily Standup with content Discussed roadmap"
kage chat "Search my Obsidian notes for KAGE"
```

### 3. General Commands & Telemetry
```bash
kage status            # System status and registered agents
kage health            # Check phone battery, storage, CPU load, and uptime
kage chat "Search the web for OpenHands AI framework"
```

## Testing

Run the complete test suite:
```bash
python3 -m unittest discover -s tests
```
