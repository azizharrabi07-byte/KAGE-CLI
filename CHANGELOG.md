## [3.0.0] — master architecture (modular, plugin-based, event-driven OS)

KAGE is redesigned as an AI Operating System where intelligence emerges from
orchestration. **Fully additive** — every prior test still passes.

### New architectural pillars
- **Orchestrator** (`core/orchestrator.py`) — the always-on conductor: plan →
  select agents on demand → execute → merge → store memory → terminate.
- **Event Bus** (`core/events.py`) — hierarchical pub/sub; agents never call
  each other directly.
- **Tool Manager** (`core/tool_manager.py`) — single gateway to filesystem/git/
  terminal/browser/memory/search; agents never touch tools directly.
- **Memory Service** (`core/memory_service.py`) — 5 layers (session/project/
  user/knowledge/longterm) behind one shared interface.
- **Planner** (`core/planner.py`) — decomposes goals into execution plans.
- **Plugin System** (`core/plugins.py`) — auto-discovers `manifest.yaml` plugins.

### Flagship: Harness Agent (`agents/harness/`)
Continuous improvement — evaluate, benchmark (latency/p95/variance → weighted
health score), compare baseline vs candidate, and propose upgrades **without
deploying them** (always `requires_approval`).

### Bridge Agents (`agents/bridge/`)
- `BridgeAgent` base + **OpenCode** and **OpenClaw** bridges.
- Thin adapters over external systems; graceful degradation when absent.
- KAGE builds bridges, never clones.

### Sample plugin (`kage/plugins/summarizer/`)
Full plugin layout: manifest.yaml, system_prompt.md, agent.py, workflow.py,
tools.py, tests/, docs/.

### Docs, tests, benchmarks
- `docs/ARCHITECTURE_V2.md`, `docs/MIGRATION.md`.
- `benchmarks/run_benchmarks.py` — per-subsystem latency/health baselines.
- `kage/tests/test_v2_architecture.py` (52 tests). Full suite: 284 assertions.

## [2.1.0] — supervisor now ACTS (shell, file edit, create_agent)

Kage is no longer reply-only. The supervisor parses action blocks from the LLM
(or rule-based fallback) and executes them, folding results back into the
response that Discord/CLI render.

### core/actions.py (new)
- `parse_actions(text)` — extracts JSON action blocks (fenced or bare), returns
  the cleaned display text.
- `ActionExecutor` — executes `shell`, `file_write` (create/overwrite/append),
  `create_agent` (scaffolds `agents/<name>/` + auto-registers).
- Tiered safety: FORBIDDEN (fork bombs, dd/mkfs to devices) never run; DANGEROUS
  (`rm -rf /`, force push, sudo, shutdown) require `allow_destructive`; normal
  commands (`ls`, `git add/commit/push`, file edits) run immediately.
- `ACTION_SCHEMA` injected into LLM context so the model knows the action format.

### supervisor.py
- `think()` now runs actions from the LLM reply and returns results in
  `Response.side_effects` + the rendered text.
- No-LLM rule-based fallback: "list files" → `ls`, "create agent X" → scaffold.
- Normal chat is unaffected (no action block ⇒ plain reply).

### Transports
- Discord (`/kage chat …`) and CLI (`kage chat …`) need **no changes** — they
  already render `Response.text`, which now includes action results.

### Config
- `KAGE_ROOT` (project root for actions), `KAGE_ALLOW_DESTRUCTIVE=1`
  (run destructive commands without confirmation).

### Tests
- `kage/tests/test_actions.py`: 46 tests (parse, executor, safety tiers,
  supervisor integration with a mock LLM). Full suite: 232 assertions, all green.

## [2.0.0] — final production release

### Agents (real implementations replace placeholders)
- **WhatsApp** (`agents/whatsapp/`): Baileys REST bridge client — QR auth, session
  restore, send/receive, reconnection, health checks. Degrades gracefully.
- **Obsidian** (`agents/obsidian/`): Local REST API — list vaults, read/write/append
  files, search. API-token auth.
- **Meta** (`agents/meta/`): self-upgrade — `upgrade.check` (git fetch + rev
  compare), `upgrade.apply` (pull + tests, requires `confirm=True`).
- **System** (`agents/system/`): device health — battery (termux-api / sysfs),
  storage (statvfs), CPU (/proc/loadavg), memory (/proc/meminfo). No psutil.

### Unified integration architecture
- `BaseIntegration` ABC: `connect/disconnect/health_check/send/receive`.
- Shared retry/timeout/backoff + auto-reconnect via `core.health`.
- Structured `ToolResult` envelope + observability on every call.

### Comprehensive testing
- 73 pytest test functions / 186 assertions across 10 files, all passing.
- Coverage **82%** (`pytest --cov`), excluding entry-point/SDK-transport glue.

### Documentation (production grade)
- `docs/`: ARCHITECTURE, DEVELOPER, API, USER, TROUBLESHOOTING.
- `examples/workflows/`: onboarding, retry_demo, research_pipeline.

### Security hardening
- `validate_shell` now blocks command substitution (`$()`, backticks, `${}`).
- `sanitize_path`, `sanitize_text`, `escape_shell_arg`, `restrict_to_sandbox`.
- Secrets env-only + masked in logs.

### Packaging & DevOps
- `pyproject.toml` (PEP 621) for optional PyPI packaging.
- `.coveragerc`; CI runs all 10 test files.

## [1.0.0] — supervisor-discord (Phases 3-8)

Additive delivery on top of the existing supervisor (Phases 1-2). No existing
file's behavior is changed; everything below is new and opt-in.

### Phase 3 — Production CLI & configuration
- `kage/cli/repl.py`: interactive REPL with slash commands
  (`/help /agents /models /providers /config /secrets /workflows /shell /health /exit`).
- Batch modes (`--json`, `--yaml`) and `--dry-run` for scripting.
- First-run config wizard (`kage.core.config.wizard`) writes `~/.kage/config.json`.

### Phase 4 — Integration layer
- `kage/core/result.py`: universal `ToolResult` envelope (status/data/error).
- `kage/core/health.py`: `run_with_retry` (exponential backoff + timeout) and
  `probe` with an auto-reconnect attempt, usable by every integration.

### Phase 5 — Workflow engine
- `kage/core/workflows/branching.py`: conditional `if`/`else` branching and
  per-step retry with backoff; resumable execution.

### Phase 6 — Performance, security, observability
- `kage/core/secrets.py`: env-only secret store + log scrubbing.
- `kage/core/sandbox.py`: input sanitisation + allow-listed shell sandbox.
- `kage/core/observability.py`: structured JSON logs (`~/.kage/logs/`),
  metrics and trace spans (agent decision chain).

### Phase 7 — Testing & documentation
- `kage/tests/test_phases_3_8.py`: 38 unit tests (runnable as a script or via
  pytest); wired into `.github/workflows/ci.yml`.
- `docs/`: ARCHITECTURE.md, DEVELOPER.md, API.md, TROUBLESHOOTING.md.
- `examples/workflows/`: onboarding.json (branching) + retry_demo.json.

### Phase 8 — DevOps
- `__version__ = "1.0.0"`; `release.yml` creates a release on `v*.*.*` tags.
- `control-plane-ci.yml` quality-gates the optional Next.js control plane.

### Optional: web control plane (`control-plane/`)
A runnable Next.js + PostgreSQL realization of Phases 3-8 (dashboard, agents,
workflows, integrations, observability, configuration, docs) sharing the same
`ToolResult` and workflow contracts. Not required to use the Python CLI.

## [0.1.0]
- Supervisor daemon + IPC, multi-agent registry, Discord (primary) + Telegram,
  tool framework (browser/shell/memory/crew), SQLite workflow engine.
