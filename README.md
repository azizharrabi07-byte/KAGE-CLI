# KAGE OS — Personal AI Operating System

A modular, high-performance CLI & Web-based AI operating system for your phone (Termux/Android), Linux, and macOS. Powered natively by Google Gemini 2.5 Flash, equipped with built-in **Browser-Use**, **OpenHands Sandbox**, **MCP Engine**, and **CrewAI Orchestrator** features accessible across all personal agents (`whatsapp`, `trilium`, `system`, `meta`).

## System Architecture

- **`core/features/`** (Universal Core Capabilities)
  - `browser.py` (`BrowserFeature`): Live DuckDuckGo web search, URL fetching, link parsing, and readable article text extraction.
  - `openhands.py` (`OpenHandsFeature`): Sandboxed shell command execution, inline Python evaluation, and workspace file synthesis.
  - `mcp.py` (`MCPFeature`): Model Context Protocol engine connecting Kage to remote or local MCP tool servers.
  - `crew.py` (`CrewFeature`): Multi-role sequential agent team task orchestrator.
- **`agents/`** (Domain Personal Agents)
  - `whatsapp`: Baileys microservice bridge (`localhost:3030`) for messaging.
  - `trilium`: [TriliumDroid](https://github.com/FliegendeWurst/TriliumDroid) / Trilium Notes ETapi mobile note integration.
  - `system`: Phone telemetry (battery, storage, CPU, uptime).
  - `meta`: Self-upgrade agent (`git pull`, test suite verification).
- **`core/`**
  - `brain.py`: Native **Google Gemini API** (`gemini-2.5-flash`) brain with automated JSON action extraction.
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

### 2. General CLI Commands & Built-in Features
```bash
kage status            # System status and core feature capabilities
kage health            # Check phone battery, storage, CPU load, and uptime
kage chat "Search the web for OpenHands AI framework"
kage chat "Run Python code to calculate 2^32"
```

### 3. Domain Agents Management
```bash
kage agent list        # List domain personal agents
kage agent wake trilium --task '{"action":"list_notes"}'
kage agent wake whatsapp --task '{"action":"status"}'
```

## Testing

Run the complete test suite:
```bash
python3 -m unittest discover -s tests
```
