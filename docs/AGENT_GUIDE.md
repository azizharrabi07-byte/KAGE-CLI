# KAGE OS — Agent Guide

## Agent Class Hierarchy

KAGE OS provides standard base classes under `core/agents/`:

* **`BaseAgent`**: Abstract parent contract supporting tool registration, cancellation, metrics, and planning hooks (`plan()`, `reason()`, `reflect()`).
* **`TaskAgent`**: Specialized for structured domain task execution.
* **`ChatAgent`**: Specialized for natural language chat routing.
* **`ToolAgent`**: Wraps external tools and API endpoints.
* **`PlanningAgent`**: Constructs step-by-step sequential execution blueprints.
* **`MemoryAgent`**: Manages user memory retrieval and fact extraction.
* **`ExecutionAgent`**: Evaluates sandboxed terminal scripts and code synthesis.
* **`BackgroundAgent`**: Runs background workers and long-polling listeners.

## Domain Personal Agents

* **`obsidian`**: Read/write notes in Obsidian vault `KAGE` via Local REST API (`localhost:27123`).
* **`whatsapp`**: Send and receive WhatsApp messages via Baileys microservice bridge (`localhost:3030`).
* **`telegram`**: Long-polling Telegram bot interface (@Mini_kage_bot).
* **`system`**: Real-time phone health telemetry (battery level, storage usage, CPU load, uptime).
* **`meta`**: Self-upgrade engine via automated `git pull` and unittest execution.
