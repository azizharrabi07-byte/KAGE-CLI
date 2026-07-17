# KAGE OS — Production AI Operating System (Phases 6 & 7 Completed)

A modular, high-performance, local terminal-based AI operating system designed for **Termux (Android)** and Linux/macOS command-line environments. Powered natively by **Google Gemini 2.5 Flash** with automated model fallbacks, **Production CLI Engine** (`core/cli/`), **Multi-Type Memory Engine** (`core/memory/`), **Modular Prompt Architecture** (`core/prompts/`), an **Extensible Agent Framework** (`core/agents/`), **Unified Integration Layer** (`core/integrations/`), persistent multi-step **Workflow Engine** (`core/workflows.py`), Telegram Bot integration (@Mini_kage_bot), Obsidian Local REST API, WhatsApp microservice bridge, phone health telemetry, and universal core OS features for **Browser-Use**, **OpenHands Sandbox**, **Awesome MCP Protocol**, and **CrewAI Orchestrator**.

---

## Architecture Overview (Phases 6 & 7)

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
│ ADVANCED MEMORY ENGINE    │  │  EXTENSIBLE AGENT FRAMEWORK│  │ UNIFIED INTEGRATION LAYER │
│     (core/memory/)        │  │      (core/agents/)        │  │    (core/integrations/)   │
├───────────────────────────┤  ├───────────────────────────┤  ├───────────────────────────┤
│ • 5 Memory Types          │  │ • BaseAgent Interface     │  │ • AbstractBaseIntegration │
│ • Vector Similarity Search│  │ • TaskAgent / ChatAgent   │  │ • ProviderRegistry        │
│ • Importance Scoring (1-10│  │ • Tool / PlanningAgent    │  │ • RetryEngine / Limiter   │
│ • TTL Expiration Cleanup  │  │ • Memory / ExecutionAgent │  │ • Dynamic PluginLoader    │
│ • Memory Summarization    │  │ • AgentRunner Parallel Pool│  │ • 7 Production Providers  │
└───────────────────────────┘  └───────────────────────────┘  └───────────────────────────┘
```

---

## Key Phase 6 & 7 Architectural Upgrades

### 1. Phase 6 — Production CLI Engine (`core/cli/`)
* **`TableFormatter`**: High-contrast border alignment for CLI data tables.
* **`OutputFormatter`**: Renders responses in plain text, structured JSON (`--json`), or YAML (`--yaml`).
* **`CLICompleter`**: Readline Tab-autocompletion for interactive slash commands, subcommands, and flags.
* **`ConfigWizard`**: Interactive step-by-step setup guide for initial KAGE OS configuration.
* **`CommandRunner` & `ExecutionFlags`**: Supports dry-run execution simulation (`--dry-run`), debug logging (`--debug`), and verbose output (`--verbose`).

### 2. Phase 7 — Advanced Memory Engine (`core/memory/`)
* **5 Standard Memory Types**:
  1. `CONVERSATION` — Short-turn dialogue context.
  2. `KNOWLEDGE` — Permanent user facts and domain rules.
  3. `WORKING` — Active task execution buffer.
  4. `EPISODIC` — Timestamped event records.
  5. `SEMANTIC` — Vector-indexed memory documents.
* **`SemanticIndex`**: Pure Python TF-IDF vectorizer and Cosine Similarity search index.
* **Importance Scoring ($1.0..10.0$)**: Ranks memories by significance to prioritize context loading.
* **TTL Expiration Engine**: Automatic background cleanup of temporary working memory records.

---

## Quick Start & Commands

```bash
# 1. Interactive Config Wizard
python3 kage_cli.py

# 2. Start Background Daemon
kage daemon start

# 3. Interactive Terminal Shell
kage
```

---

## Verification & Automated Unit Testing

```bash
python3 -m unittest discover -s tests
```
