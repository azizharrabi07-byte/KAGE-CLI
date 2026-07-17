# KAGE OS — Production AI Operating System (Phases 8 & 9 Completed)

A modular, high-performance, local terminal-based AI operating system designed for **Termux (Android)** and Linux/macOS command-line environments. Powered natively by **Google Gemini 2.5 Flash** with automated model fallbacks, **Hardened Security Framework** (`core/security/`), **Standardized Tool Architecture** (`core/tools/`), **Production CLI Engine** (`core/cli/`), **Multi-Type Memory Engine** (`core/memory/`), **Modular Prompt Architecture** (`core/prompts/`), an **Extensible Agent Framework** (`core/agents/`), **Unified Integration Layer** (`core/integrations/`), persistent multi-step **Workflow Engine** (`core/workflows.py`), Telegram Bot integration (@Mini_kage_bot), Obsidian Local REST API, WhatsApp microservice bridge, phone health telemetry, and universal core OS features for **Browser-Use**, **OpenHands Sandbox**, **Awesome MCP Protocol**, and **CrewAI Orchestrator**.

---

## Architecture Overview (Phases 8 & 9)

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                    KAGE OS PRODUCTION CLI ENGINE (core/cli/)              │
│  Tab Completer | Table & Output Formatters | Config Wizard | Execution Flags │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ Unix Domain Socket IPC (~/.kage/kage.sock)
┌────────────────────────────────────▼──────────────────────────────────────┐
│                    SUPERVISOR DAEMON (kage.py)                            │
│  Auto-Spawns Workers • Coordinates Multi-Type Memory Engine & AgentRunner  │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ Shared Context
      ┌──────────────────────────────┼──────────────────────────────┐
      │                              │                              │
┌─────▼─────────────────────┐  ┌─────▼─────────────────────┐  ┌─────▼─────────────────────┐
│ STANDARDIZED TOOL FRAMEWORK│  │ HARDENED SECURITY ENGINE │  │ UNIFIED INTEGRATION LAYER │
│      (core/tools/)        │  │    (core/security/)       │  │    (core/integrations/)   │
├───────────────────────────┤  ├───────────────────────────┤  ├───────────────────────────┤
│ • BaseTool Specification  │  │ • SafePathValidator       │  │ • AbstractBaseIntegration │
│ • ToolMetadata & Schemas  │  │ • InputSanitizer          │  │ • ProviderRegistry        │
│ • ToolResult Data Standard│  │ • SecretRedactor          │  │ • RetryEngine / Limiter   │
│ • ToolRegistry Dispatcher │  │ • SecurityManager Policies│  │ • Dynamic PluginLoader    │
│ • Bash/Python/File/Web    │  │ • Token Redaction Rules   │  │ • 7 Production Providers  │
└───────────────────────────┘  └───────────────────────────┘  └───────────────────────────┘
```

---

## Key Phase 8 & 9 Architectural Upgrades

### 1. Phase 8 — Standardized Tool Framework (`core/tools/`)
* **`BaseTool`**: Abstract contract requiring parameter schema validation, timeouts, retries, and structured logging (`ToolResult`).
* **`PermissionLevel`**: Formal classification of tools into `SAFE`, `SENSITIVE`, and `CRITICAL`.
* **`ToolRegistry`**: Central tool repository matching requests against metadata schemas.
* **Standard Tool Library**:
  * `BashTool` (`bash_execute`) — Parameterized sandboxed shell execution.
  * `PythonTool` (`python_eval`) — Isolated inline Python script evaluation.
  * `FileTool` (`file_ops`) — Safe workspace reading and writing with traversal checks.
  * `WebTool` (`web_search`) — DuckDuckGo search and page text extraction.
  * `MemoryTool` (`user_memory`) — Memory item search, fact storage, and recall.

### 2. Phase 9 — Hardened Security Framework (`core/security/`)
* **`SafePathValidator`**: Resolves paths and enforces strict authorized workspace root boundaries (`/home/user/KAGE-CLI` or `~/.kage`), blocking directory traversal attacks (`../`).
* **`SecretRedactor`**: Scans plain text logs, JSON payloads, exceptions, and stack traces for sensitive credentials (Gemini keys, Telegram tokens, Obsidian keys) and masks them automatically (`AQ.A***[REDACTED]***K2Tg`).
* **`SecurityManager`**: Enforces system-wide authorization policies across CLI, IPC, and remote channels.

---

## Quick Start & Commands

```bash
# 1. Interactive Config Wizard
python3 kage_cli.py

# 2. Start Background Daemon
kage daemon start

# 3. Open Interactive Terminal Shell
kage
```

---

## Verification & Automated Unit Testing

```bash
python3 -m unittest discover -s tests
```
