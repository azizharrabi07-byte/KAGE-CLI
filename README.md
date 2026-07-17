# KAGE OS — Production AI Operating System (Phases 4 & 5 Completed)

A modular, high-performance, local terminal-based AI operating system designed for **Termux (Android)** and Linux/macOS command-line environments. Powered natively by **Google Gemini 2.5 Flash** with automated model fallbacks, a **Modular Prompt Architecture** (`core/prompts/`), an **Extensible Agent Framework** (`core/agents/`), **Unified Integration Layer** (`core/integrations/`), persistent multi-step **Workflow Engine** (`core/workflows.py`), Telegram Bot integration (@Mini_kage_bot), Obsidian Local REST API, WhatsApp microservice bridge, phone health telemetry, and universal core OS features for **Browser-Use**, **OpenHands Sandbox**, **Awesome MCP Protocol**, and **CrewAI Orchestrator**.

---

## Architecture Overview (Phases 4 & 5)

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                    KAGE OS TERMINAL FRONTEND (kage_cli.py)                │
│  kage (REPL) | kage chat | kage telegram | kage schedule | kage status    │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ Unix Domain Socket IPC (~/.kage/kage.sock)
┌────────────────────────────────────▼──────────────────────────────────────┐
│                    SUPERVISOR DAEMON (kage.py)                            │
│  Auto-Spawns Background Services • Manages AgentRunner Thread Pool        │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ Shared Context
      ┌──────────────────────────────┼──────────────────────────────┐
      │                              │                              │
┌─────▼─────────────────────┐  ┌─────▼─────────────────────┐  ┌─────▼─────────────────────┐
│ MODULAR PROMPT ENGINE     │  │  EXTENSIBLE AGENT FRAMEWORK│  │ UNIFIED INTEGRATION LAYER │
│     (core/prompts/)       │  │      (core/agents/)        │  │    (core/integrations/)   │
├───────────────────────────┤  ├───────────────────────────┤  ├───────────────────────────┤
│ • PromptTemplate          │  │ • BaseAgent Interface     │  │ • AbstractBaseIntegration │
│ • PromptVersionRegistry   │  │ • TaskAgent / ChatAgent   │  │ • ProviderRegistry        │
│ • PromptCompressor        │  │ • Tool / PlanningAgent    │  │ • RetryEngine / Limiter   │
│ • ContextBuilder          │  │ • Memory / ExecutionAgent │  │ • Dynamic PluginLoader    │
│ • 12 Standard Blueprints  │  │ • AgentRunner Parallel Pool│  │ • 7 Production Providers  │
└───────────────────────────┘  └───────────────────────────┘  └───────────────────────────┘
```

---

## Key Phase 4 & 5 Architectural Features

### 1. Modular Prompt Architecture (`core/prompts/`)
All hardcoded prompts extracted into a central, version-controlled templating framework:
* **`PromptTemplate`**: Interpolates `$variable` and `{{variable}}` blueprints with typing validation.
* **`PromptVersionRegistry`**: Maintains prompt versioning (`v1.0`, `v2.1`, `latest`) and variation registries.
* **`PromptCompressor`**: Context window optimizer performing smart whitespace pruning, line deduplication, and budget truncation.
* **`ContextBuilder`**: Assembles user prompts, chat history windows, and persistent memory context into LLM payloads.
* **Standard Specialized Prompts**: `SystemPrompt`, `DeveloperPrompt`, `ToolPrompt`, `PlannerPrompt`, `ReasoningPrompt`, `MemoryPrompt`, `SummarizerPrompt`, `AgentPrompt`, `ReflectionPrompt`, `ExecutionPrompt`, `SafetyPrompt`, `ErrorRecoveryPrompt`.

### 2. Extensible Agent Framework (`core/agents/`)
* **`BaseAgent`**: Abstract Base Class defining standard agent state, tool registration, cancellation signals, metrics collection, and reasoning hooks (`plan()`, `reason()`, `reflect()`).
* **Specialized Class Hierarchy**:
  * `TaskAgent` — Domain task execution.
  * `ChatAgent` — Multi-turn conversational routing.
  * `ToolAgent` — Tool & API integration wrappers.
  * `PlanningAgent` — Sequential execution plan construction.
  * `MemoryAgent` — Fact extraction & user context storage.
  * `ExecutionAgent` — Sandboxed terminal shell & Python evaluation.
  * `BackgroundAgent` — Long-polling workers & persistent service daemons.
* **`AgentRunner`**: Thread pool worker manager (`ThreadPoolExecutor`) enabling concurrent multi-agent task execution.
* **`AgentMetrics`**: Latency, invocation, success, and failure analytics tracking per agent.

---

## Quick Start & Commands

```bash
# 1. Start Background Daemon
kage daemon start

# 2. Open OpenCode Interactive Terminal REPL
kage
```

---

## Verification & Automated Unit Testing

```bash
python3 -m unittest discover -s tests
```
