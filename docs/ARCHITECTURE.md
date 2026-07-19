# KAGE OS — Architecture

KAGE OS is layered so the **supervisor** (transport-agnostic brain) never talks
to the outside world directly — it delegates to **agents** and **tools**.

```
┌─ Transports ──────────────────────────────┐
│  CLI (kage repl) · Discord · Telegram      │   Phase 3 (CLI)
└───────────────────┬───────────────────────┘
┌─ Supervisor (kage.core) ──────────────────┐
│  intent · memory · sessions · routing      │
│  registry (wake/execute/sleep)             │
└──┬───────────────┬──────────────┬─────────┘
   │ agents        │ tools        │ workflows
   discord         browser        engine.py (SQLite)        Phase 5
   telegram        shell          branching.py (if/else+retry)
   whatsapp        memory         observability             Phase 6
   obsidian        crew           secrets · sandbox · cache
   system/meta                    health (retry/timeout)    Phase 4
```

## Phases 3-8 modules (additive, this branch)
- `kage/core/result.py` — universal `ToolResult` envelope (status/data/error).
- `kage/core/health.py` — `run_with_retry` (backoff + timeout), `probe`.
- `kage/core/secrets.py` — env-only secret store + log scrubbing.
- `kage/core/observability.py` — structured JSON logs + metrics + traces.
- `kage/core/sandbox.py` — input sanitisation + allow-listed shell sandbox.
- `kage/core/workflows/branching.py` — conditional branching + per-step retry.
- `kage/cli/repl.py` — production REPL with slash commands + batch modes.
- `control-plane/` — optional Next.js web control plane (same contracts).

## Data flow
1. A trigger (CLI, Discord slash command, scheduled tick) calls the supervisor.
2. It resolves intent + memory, routes to an agent/tool, runs it with retry.
3. Each unit of work emits a structured log, a metric and a trace span.
4. Workflow state persists (SQLite) so runs resume after a restart.
