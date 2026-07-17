# KAGE OS — Production AI Operating System (Phases 2 & 3 Completed)

A modular, high-performance, local terminal-based AI operating system designed for **Termux (Android)** and Linux/macOS command-line environments. Powered natively by **Google Gemini 2.5 Flash** with automated model fallbacks, a **Unified Integration Layer** (`core/integrations/`), persistent multi-step **Workflow Execution Engine** (`core/workflows.py`), Telegram Bot integration (@Mini_kage_bot), Obsidian Local REST API, WhatsApp microservice bridge, phone health telemetry, and universal core OS features for **Browser-Use**, **OpenHands Sandbox**, **Awesome MCP Protocol**, and **CrewAI Orchestrator**.

---

## Architecture Overview (Phases 2 & 3)

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                    KAGE OS TERMINAL FRONTEND (kage_cli.py)                │
│  kage (REPL) | kage chat | kage telegram | kage schedule | kage status    │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ Unix Domain Socket IPC (~/.kage/kage.sock)
┌────────────────────────────────────▼──────────────────────────────────────┐
│                    SUPERVISOR DAEMON (kage.py)                            │
│  Auto-Spawns Telegram Worker • Manages WorkflowEngine • Shared Context    │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ Unified Provider Registry
      ┌──────────────────────────────┼──────────────────────────────┐
      │                              │                              │
┌─────▼─────────────────────┐  ┌─────▼─────────────────────┐  ┌─────▼─────────────────────┐
│  GEMINI 2.5 FLASH BRAIN   │  │   UNIVERSAL OS FEATURES   │  │ UNIFIED INTEGRATION LAYER │
│    (core/brain.py)        │  │     (core/features/)      │  │    (core/integrations/)   │
├───────────────────────────┤  ├───────────────────────────┤  ├───────────────────────────┤
│ • Direct Google REST API  │  │ • browser (browser-use)   │  │ • AbstractBaseIntegration │
│ • Automated Model Failover│  │ • openhands (Code/Sandbox)│  │ • ProviderRegistry        │
│ • ReAct Reasoning Loop    │  │ • mcp (Awesome MCP)       │  │ • RetryEngine / Limiter   │
│ • Per-User Memory Context │  │ • crew (CrewAI Teams)     │  │ • Dynamic PluginLoader    │
└───────────────────────────┘  └───────────────────────────┘  └───────────────────────────┘
```

---

## Key Phase 2 & 3 Upgrades

### 1. Unified Integration Layer (`core/integrations/`)
Every external service and AI provider inherits from `AbstractBaseIntegration`:
* **`ProviderRegistry`**: Dynamic registration and lookup of active provider singletons (`GeminiProvider`, `GroqProvider`, `OpenRouterProvider`, `OllamaProvider`, `ObsidianProvider`, `WhatsAppProvider`, `TelegramProvider`).
* **`RetryEngine`**: Exponential backoff with jitter and configurable retry limits.
* **`RateLimiter`**: Sliding window rate limiter preventing API quota exhaustion.
* **`HealthStatus`**: Standardized health check monitoring with latency tracking in milliseconds.
* **`PluginLoader`**: Scans `~/.kage/plugins` and `plugins/` to register third-party integration classes dynamically.

### 2. Multi-Step Workflow Engine (`core/workflows.py`)
* **Persistence & Context Interpolation**: Persists structured multi-step pipelines in `kage.db` with status state machines (`pending` $\rightarrow$ `running` $\rightarrow$ `completed` / `failed`).
* **Step Data Chaining**: Step $N$ results are automatically made available to step $N+1$ via double-curly interpolation (`{{step_1.output}}`).

---

## Quick Start & Commands

```bash
# 1. Start Supervisor Daemon (spawns background workers and workflow engine)
kage daemon start

# 2. Open Interactive Terminal Shell
kage
```

---

## Verification & Automated Unit Testing

```bash
python3 -m unittest discover -s tests
```
