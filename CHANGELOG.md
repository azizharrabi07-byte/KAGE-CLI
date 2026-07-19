# Changelog

All notable changes follow [Semantic Versioning](https://semver.org/).
Canonical version: `kage/__init__.py` → `__version__`.

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
