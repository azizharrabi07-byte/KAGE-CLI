# KAGE OS — Personal AI Agent System

A modular, high-performance CLI-based AI operating system for your phone (Termux/Android), Linux, and macOS. Powered natively by Google Gemini 2.5 Flash and connected to phone health, WhatsApp, Trilium / TriliumDroid notes, Model Context Protocol (MCP) servers, autonomous web browsing, and software control sandboxes.

## Architecture & Agents

- **`core/`**
  - `brain.py`: LLM wrapper natively supporting **Google Gemini API** (`gemini-2.5-flash`) and OpenRouter/OpenAI compatible models with automated JSON action block extraction.
  - `memory.py`: SQLite WAL database for trace logging, workflows, and cron schedule persistence (`kage.db`).
  - `permissions.py`: Safety permission model distinguishing read/health checks from sensitive actions.
  - `scheduler.py`: Background cron-style task scheduler with minute-level execution tracking.
- **`agents/`**
  - `whatsapp`: Baileys microservice bridge (`localhost:3030`) with persistent background process and JID auto-formatting.
  - `trilium`: [TriliumDroid](https://github.com/FliegendeWurst/TriliumDroid) / Trilium Notes ETapi integration for mobile hierarchical note management.
  - `mcp`: [Awesome MCP](https://github.com/punkpeye/awesome-mcp-servers) client bridge connecting Kage to remote and local Model Context Protocol tool & resource servers (JSON-RPC 2.0).
  - `browser`: [browser-use](https://github.com/browser-use/browser-use) inspired web browsing agent for live web searches, article fetching, HTML link parsing, and content extraction.
  - `openhands`: [OpenHands](https://github.com/OpenHands/OpenHands) inspired software execution & control agent for sandboxed terminal command execution, python evaluation, and file writing.
  - `system`: Cross-platform phone health inspection (battery, storage, CPU load, uptime).
  - `meta`: Self-upgrade agent for automated `git pull`, automated testing, and daemon reload.
- **`skills/`**
  - `helpers.py`: Hot-reloadable utility functions and safe JSON parser.
- **`kage.py`**: Background supervisor daemon and Unix socket IPC server (`~/.kage/kage.sock`).
- **`kage_cli.py`**: Rich user CLI frontend.
- **`tests/`**: Comprehensive automated test suite.

## Install

```bash
git clone https://github.com/azizharrabi07-byte/KAGE-CLI.git
cd KAGE-CLI
bash setup.sh
```

## Quick Start & Usage

### 1. Daemon Management
```bash
kage daemon start      # Start the background supervisor service
kage daemon status     # Check daemon and system status
kage daemon stop       # Safely stop the supervisor daemon
```

### 2. General CLI Commands
```bash
kage status            # Show registered agents, loaded memory, active schedules
kage health            # Check phone battery, storage, CPU load, and uptime
kage chat "hello"      # Direct interaction with Kage AI brain (Gemini 2.5)
```

### 3. Agent Capabilities
```bash
kage agent list        # List all 8 registered agents and status
kage chat "Search the web for OpenHands AI agent framework"
kage agent wake browser --task '{"action":"search", "query":"Model Context Protocol"}'
kage agent wake mcp --task '{"action":"list_servers"}'
kage agent wake openhands --task '{"action":"status"}'
kage agent wake trilium --task '{"action":"list_notes"}'
kage agent create mybot # Scaffold a new agent directory
```

### 4. Scheduler (Cron Jobs)
```bash
kage schedule add --cron "0 9 * * *" --agent system --task '{"action":"health"}'
kage schedule list
kage schedule delete 1
```

### 5. Execution Traces
```bash
kage trace list        # View recent execution history
kage trace show 1      # Detailed view of trace ID 1
```

## Testing

Run the complete test suite:
```bash
python3 -m unittest discover -s tests
```

## Configuration

Settings live in `config.toml` or `~/.kage/config.toml`:
```toml
[llm]
provider = "gemini"
api_key = "YOUR_GEMINI_API_KEY_HERE"
model = "gemini-2.5-flash"
base_url = "https://generativelanguage.googleapis.com/v1beta"

[trilium]
url = "http://localhost:8080"
etapi_token = "YOUR_TRILIUM_ETAPI_TOKEN"

[mcp]
servers = [
    { name = "fetch", url = "http://localhost:8000/mcp" },
    { name = "filesystem", url = "http://localhost:8001/mcp" }
]

[system]
log_level = "info"
max_retries = 3
timeout = 30
```
