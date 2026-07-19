# Changelog

All notable changes to KAGE OS follow [Semantic Versioning](https://semver.org/).
The canonical version lives in `src/lib/version.ts`.

## [3.0.0] — supervisor-discord

Phases 3–8 delivered as the KAGE OS control plane.

### Phase 3 — Configuration
- Setup wizard with provider, model, concurrency, log level and output format.
- Persistent key/value configuration store (`config` table).
- Batch-style output modes (`text` / `json` / `yaml`) selectable from config.

### Phase 4 — Integration layer
- Functional health probes for Discord, Telegram, WhatsApp, Obsidian, LLM
  providers and Postgres.
- Generic `runWithRetry` with exponential backoff and per-call timeout.
- Auto-reconnect with an extra probe attempt on failure.
- Consistent `ToolResult` envelope (`status`, `data`, `error`, `durationMs`,
  `attempts`) across all tools and integrations.

### Phase 5 — Workflow engine
- Conditional branching (`if`/`else` via `branch` on status / data / meta.code).
- Per-step retry with configurable backoff factor.
- Resumable persistence — state survives restarts (`workflows.state`).
- Run / step / pause / cancel / reset controls.

### Phase 6 — Performance, security, observability
- Two-tier response cache (in-memory + disk) with configurable TTL.
- Secret vault storing masked references only; plaintext resolves from env.
- Input sanitisation and a sandboxed, allow-listed shell tool.
- Structured JSON logs to `~/.kage/logs/kage.log` and the `logs` table.
- Metrics (response time, token usage, agent/tool calls) and decision traces.

### Phase 7 — Documentation
- In-app documentation hub: architecture, developer guide, API reference,
  examples and troubleshooting.

### Phase 8 — DevOps
- `__version__` equivalent in `src/lib/version.ts`, semver-tagged releases.
- GitHub Actions: `ci.yml` (lint, type-check, build) and `release.yml`.

## [2.0.0]
- Supervisor daemon with IPC.
- Multi-agent registry (wake / execute / sleep).
- Discord integration with slash commands.
- Tool framework (browser, shell, memory, crew).
- Initial persisted, multi-step workflow engine.

## [1.0.0]
- Initial KAGE CLI scaffold.
