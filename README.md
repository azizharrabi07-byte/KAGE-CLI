# KAGE OS — Production AI Operating System (Phases 10 & 11 Completed)

A modular, high-performance, local terminal-based AI operating system designed for **Termux (Android)** and Linux/macOS command-line environments. Powered natively by **Google Gemini 2.5 Flash** with automated model fallbacks, **Multi-Tier Caching & Async Engine** (`core/performance/`), **Comprehensive Test Automation Suite** (`tests/`), **Hardened Security Engine** (`core/security/`), **Standardized Tool Framework** (`core/tools/`), **Production CLI Engine** (`core/cli/`), **Multi-Type Memory Engine** (`core/memory/`), **Modular Prompt Architecture** (`core/prompts/`), an **Extensible Agent Framework** (`core/agents/`), **Unified Integration Layer** (`core/integrations/`), persistent multi-step **Workflow Engine** (`core/workflows.py`), Telegram Bot integration (@Mini_kage_bot), Obsidian Local REST API, WhatsApp microservice bridge, phone health telemetry, and universal core OS features for **Browser-Use**, **OpenHands Sandbox**, **Awesome MCP Protocol**, and **CrewAI Orchestrator**.

---

## Architecture Overview (Phases 10 & 11)

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                    KAGE OS PRODUCTION CLI ENGINE (core/cli/)              │
│  Tab Completer | Table & Output Formatters | Config Wizard | Execution Flags │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ Unix Domain Socket IPC (~/.kage/kage.sock)
┌────────────────────────────────────▼──────────────────────────────────────┐
│                    SUPERVISOR DAEMON (kage.py)                            │
│  Auto-Spawns Workers • Coordinates Performance Cache & Async Dispatcher   │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ Shared Context
      ┌──────────────────────────────┼──────────────────────────────┐
      │                              │                              │
┌─────▼─────────────────────┐  ┌─────▼─────────────────────┐  ┌─────▼─────────────────────┐
│ PERFORMANCE CACHE & ASYNC │  │ STANDARDIZED TOOL FRAMEWORK│  │ HARDENED SECURITY ENGINE │
│   (core/performance/)     │  │      (core/tools/)        │  │    (core/security/)       │
├───────────────────────────┤  ├───────────────────────────┤  ├───────────────────────────┤
│ • ResponseCache (Mem+Disk)│  │ • BaseTool Specification  │  │ • SafePathValidator       │
│ • TTL Automatic Expiration│  │ • ToolMetadata & Schemas  │  │ • InputSanitizer          │
│ • AsyncEngine Coroutines  │  │ • ToolResult Data Standard│  │ • SecretRedactor          │
│ • ThreadPool Execution    │  │ • ToolRegistry Dispatcher │  │ • SecurityManager Policies│
└───────────────────────────┘  └───────────────────────────┘  └───────────────────────────┘
```

---

## Key Phase 10 & 11 Architectural Upgrades

### 1. Phase 10 — Performance Optimization Engine (`core/performance/`)
* **`ResponseCache` (`core/performance/cache.py`)**: Two-tier memory and file-backed caching engine with TTL expiration for repeated prompts, web search results, and tool queries.
* **`AsyncEngine` (`core/performance/async_engine.py`)**: Non-blocking asynchronous task execution and thread pool execution wrappers (`run_in_executor`).

### 2. Phase 11 — Comprehensive Testing Suite (`tests/`)
Created a modular test framework containing 41 automated tests covering 100% of core subsystems:
* `test_cli.py` — Table formatters, JSON/YAML exporters, tab autocompletion, dry-run mode.
* `test_agents.py` — Agent metrics, task execution, parallel worker dispatch.
* `test_memory.py` — 5 memory types, TTL expiration, user fact recall.
* `test_tools.py` — BaseTool, ToolRegistry, BashTool, PythonTool, FileTool path traversal protection.
* `test_security.py` — SafePathValidator, InputSanitizer, SecretRedactor token masking.
* `test_integrations.py` — ProviderRegistry, RetryEngine exponential backoff, HealthStatus monitoring.
* `test_prompts.py` — PromptTemplate rendering, PromptVersionRegistry, ContextBuilder.
* `test_performance.py` — ResponseCache operations and AsyncEngine dispatching.
* `test_workflows.py` — WorkflowEngine multi-step execution.

---

## Quick Start & Verification

```bash
# 1. Run Automated Test Suite (41 Tests)
python3 -m unittest discover -s tests

# 2. Open Interactive Terminal REPL
kage
```
