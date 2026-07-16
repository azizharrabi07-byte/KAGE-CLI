# KAGE OS — Personal AI Agent System

A modular, high-performance CLI-based AI operating system for your phone (Termux/Android), Linux, and macOS.

## Architecture

- **`core/`**
  - `brain.py`: LLM wrapper for OpenRouter / OpenAI compatible models with structured action JSON extractor.
  - `memory.py`: SQLite WAL database for trace logging, workflows, and cron schedule persistence (`kage.db`).
  - `permissions.py`: Safety permission model distinguishing read/health checks from sensitive actions.
  - `scheduler.py`: Background cron-style task scheduler with minute-level execution tracking.
- **`agents/`**
  - `whatsapp`: Baileys microservice bridge (`localhost:3030`) with persistent background process and JID auto-formatting.
  - `obsidian`: Obsidian Local REST API interface for search, read, write, and append.
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
kage chat "hello"      # Direct interaction with Kage AI brain
```

### 3. Agent Operations
```bash
kage agent list        # List all registered agents and status
kage agent wake system --task '{"action":"health"}'
kage agent wake obsidian --task '{"action":"list_files"}'
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

Edit `config.toml` or `~/.kage/config.toml`:
```toml
[llm]
provider = "openrouter"
api_key = "YOUR_KEY_HERE"
model = "anthropic/claude-3.5-sonnet"
base_url = "https://openrouter.ai/api/v1"

[obsidian]
url = "http://localhost:27123"
api_key = "YOUR_OBSIDIAN_KEY"

[system]
log_level = "info"
max_retries = 3
timeout = 30
```
