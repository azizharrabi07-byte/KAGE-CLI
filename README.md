# KAGE OS — Personal AI Agent System

A modular, high-performance CLI & Web-based AI operating system for your phone (Termux/Android), Linux, and macOS. Powered natively by Google Gemini 2.5 Flash, equipped with an interactive OpenCode/OpenClaude-style Web Landing Page, multi-agent CrewAI orchestration, Model Context Protocol (MCP) server support, browser web searching, software execution sandboxes, WhatsApp, Trilium Notes, and phone health monitoring.

## Architecture & Agents

- **`core/`**
  - `brain.py`: LLM wrapper natively supporting **Google Gemini API** (`gemini-2.5-flash`) and OpenRouter/OpenAI compatible models with automated JSON action block extraction.
  - `memory.py`: SQLite WAL database for trace logging, workflows, and cron schedule persistence (`kage.db`).
  - `permissions.py`: Safety permission model distinguishing read/health checks from sensitive actions.
  - `scheduler.py`: Background cron-style task scheduler with minute-level execution tracking.
  - `web_ui.py`: Built-in HTTP web server serving the Control Dashboard on `http://localhost:8080`.
- **`agents/`**
  - `crew`: [CrewAI](https://github.com/crewAIInc/crewAI) multi-agent crew orchestration for multi-role sequential workflows (e.g. Researcher, Writer, Developer, Reviewer).
  - `mcp`: [Awesome MCP](https://github.com/punkpeye/awesome-mcp-servers) client bridge connecting Kage to remote and local Model Context Protocol tool & resource servers (JSON-RPC 2.0).
  - `browser`: [browser-use](https://github.com/browser-use/browser-use) web browsing agent for live web searches, article fetching, HTML link parsing, and content extraction.
  - `openhands`: [OpenHands](https://github.com/OpenHands/OpenHands) software execution & control agent for sandboxed terminal command execution, python evaluation, and file writing.
  - `whatsapp`: Baileys microservice bridge (`localhost:3030`) with persistent background process and JID auto-formatting.
  - `trilium`: [TriliumDroid](https://github.com/FliegendeWurst/TriliumDroid) / Trilium Notes ETapi integration for mobile hierarchical note management.
  - `system`: Cross-platform phone health inspection (battery, storage, CPU load, uptime).
  - `meta`: Self-upgrade agent for automated `git pull`, automated testing, and daemon reload.
- **`web/`**: Interactive OpenCode / OpenClaude / OpenHands-style landing page dashboard (`index.html`).
- **`skills/`**: Hot-reloadable utility functions and safe JSON parser (`helpers.py`).
- **`kage.py`**: Background supervisor daemon and Unix socket IPC server (`~/.kage/kage.sock`).
- **`kage_cli.py`**: Rich user CLI frontend with `kage web` launcher.
- **`tests/`**: Comprehensive automated test suite.

## Install

```bash
git clone https://github.com/azizharrabi07-byte/KAGE-CLI.git
cd KAGE-CLI
bash setup.sh
```

## Quick Start & Usage

### 1. Web Dashboard Landing Page
Launch the interactive web UI to speak with your agents and monitor phone telemetry:
```bash
kage web --port 8080
```
Open **`http://localhost:8080`** in your browser!

### 2. Daemon Management
```bash
kage daemon start      # Start the background supervisor service
kage daemon status     # Check daemon and system status
kage daemon stop       # Safely stop the supervisor daemon
```

### 3. CLI Interaction
```bash
kage status            # Show registered agents, loaded memory, active schedules
kage health            # Check phone battery, storage, CPU load, and uptime
kage chat "hello"      # Direct interaction with Kage AI brain (Gemini 2.5)
```

### 4. Agent Capabilities & Multi-Agent Crews
```bash
kage agent list        # List all 9 registered agents and status
kage chat "Search the web for OpenHands AI agent framework"
kage agent wake crew --task '{"action":"run_crew", "template":"research_writer", "topic":"Quantum Computing"}'
kage agent wake browser --task '{"action":"search", "query":"Model Context Protocol"}'
kage agent wake mcp --task '{"action":"list_servers"}'
kage agent wake openhands --task '{"action":"status"}'
kage agent wake trilium --task '{"action":"list_notes"}'
```

### 5. Scheduler (Cron Jobs) & Execution Traces
```bash
kage schedule add --cron "0 9 * * *" --agent system --task '{"action":"health"}'
kage trace list        # View recent execution history
kage trace show 1      # Detailed view of trace ID 1
```

## Testing

Run the complete test suite:
```bash
python3 -m unittest discover -s tests
```
