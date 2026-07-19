# KAGE OS — Supervisor Control Plane

> Production control plane for the **KAGE OS** multi-agent supervisor.
> This is the web realization of **Phases 3–8** of the `supervisor-discord`
> roadmap: configuration, integrations, workflows, performance, security,
> observability, documentation and DevOps.

## ⚠️ Environment note

The original roadmap targets a **Python CLI** (`kage/...`, flake8/mypy/bandit) on
the `supervisor-discord` Git branch. The build sandbox provided here is a
**Next.js + PostgreSQL (Drizzle)** stack with no Git/GitHub access. To deliver
the *substance* of Phases 3–8 in this environment, the CLI/control-plane
capability is implemented as a **fullstack web application**. Every phase maps
1:1 (see below). No existing capability contract is broken — the typed
`ToolResult` envelope, agent lifecycle and workflow semantics mirror the
supervisor spec.

| Roadmap phase | Delivered in this control plane |
|---|---|
| **3** Config / CLI | Configuration wizard + persistent settings, output modes |
| **4** Integrations | Health probes, retry/timeout, auto-reconnect, `ToolResult` |
| **5** Workflows | Branching, per-step retry+backoff, resumable persistence |
| **6** Perf/Sec/Obs | Cache, secret vault, sandboxed shell, logs/metrics/traces |
| **7** Docs | In-app hub (architecture, dev, API, examples, troubleshooting) |
| **8** DevOps | CI + release workflows, semver, CHANGELOG |

## Stack

- **Next.js 16** (App Router, React 19) — server + client components
- **PostgreSQL** via **Drizzle ORM**
- **Tailwind CSS v4**

## Architecture

```
src/
  db/            schema (agents, workflows, integrations, logs, metrics, traces, secrets, config)
  lib/           domain logic: workflow engine, health/retry, cache, runtime(secrets/sandbox),
                 observability, config, seed, types, version
  components/    Sidebar + shared UI primitives
  app/
    page.tsx              Overview dashboard (server, seeds on first boot)
    agents/               Registry: wake / execute / sleep + decision traces
    workflows/            Engine: step graph, branching, run/cancel/reset
    integrations/         Health dashboard
    observability/        Logs / metrics / traces
    config/               Setup wizard, secret vault, cache
    docs/                 Documentation hub
    api/                  REST surface (see in-app API reference)
```

## Local development

```bash
npm install
npx drizzle-kit push        # apply schema to Postgres
npm run dev                 # http://localhost:3000
```

Validation (mirrors CI):

```bash
npm run lint
npm run typecheck
npm run build
```

## Key concepts

- **ToolResult envelope** — every tool/integration returns
  `{ status, data, error, durationMs, attempts }`.
- **Workflow state** — persisted in `workflows.state` so a run resumes after a
  restart; `currentStepId` points at the next step.
- **Secrets** — only masked references are stored; real values are read from the
  environment at runtime and are never logged.

## Versioning

`src/lib/version.ts` is the single source of truth. Releases are cut by pushing a
`v*.*.*` tag, which triggers `.github/workflows/release.yml`.
