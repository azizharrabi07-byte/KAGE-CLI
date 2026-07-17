# KAGE OS — Architecture Guide

## System Overview

KAGE OS is a personal AI Operating System engineered for mobile terminal environments (Termux/Android) as well as Linux and macOS command-line environments. It features a Supervisor Daemon communicating over Unix Domain Sockets, multi-provider LLM failover, a modular prompt engine, standardized tool interfaces, persistent multi-type memory, and an extensible agent framework.

## Component Diagram

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                    KAGE OS TERMINAL FRONTEND (kage_cli.py)                │
│  Interactive REPL | Slash Commands | Config Wizard | Autocomplete Format  │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ Unix Domain Socket IPC (~/.kage/kage.sock)
┌────────────────────────────────────▼──────────────────────────────────────┐
│                    SUPERVISOR DAEMON (kage.py)                            │
│  Auto-Spawns Workers • Coordinates Performance Cache & AgentRunner         │
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
└───────────────────────────┘  └───────────────────────────┘  └───────────────────────────┘
```

## Key Layers

1. **Frontend CLI & IPC (`kage_cli.py`)**: Readline REPL shell supporting slash commands, autocomplete, output formatting (JSON/YAML), and dry-run execution modes.
2. **Supervisor Daemon (`kage.py`)**: Manages the background socket IPC loop, background workers (Telegram polling bot), and background cron scheduler.
3. **Brain Engine (`core/brain.py`)**: Routes prompts to active LLM providers (Gemini, Groq, OpenRouter, Ollama) with multi-model failover chains and dynamic config reloading.
4. **Integrations Layer (`core/integrations/`)**: Abstract contract (`AbstractBaseIntegration`), `ProviderRegistry`, `PluginLoader`, `RetryEngine`, and `RateLimiter`.
5. **Memory System (`core/memory/`)**: 5-type memory engine (`CONVERSATION`, `KNOWLEDGE`, `WORKING`, `EPISODIC`, `SEMANTIC`), vector similarity search index (TF-IDF), importance scoring, and TTL cleanup.
6. **Tool Framework (`core/tools/`)**: Standardized tool contract (`BaseTool`, `ToolRegistry`, `ToolMetadata`, `ToolResult`) covering sandboxed shell execution, Python evaluation, file operations, web search, and memory recall.
