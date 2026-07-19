# KAGE OS — Migration Plan (v1 → v2)

The v2 architecture is **additive**. Nothing in the existing supervisor, CLI,
Discord agent, memory, or sessions was removed or broken — every prior test
(284 assertions) still passes. This document shows how to adopt the new
primitives incrementally.

## What changed vs v1

| Concern | v1 (existing) | v2 (new, additive) |
|---|---|---|
| Routing | `Supervisor.think()` intent rules | `Planner` produces an `ExecutionPlan` |
| Tools | `ToolRegistry` (agents call directly) | `ToolManager` gateway (agents go through it) |
| Memory | `MemoryStore` (flat, per-user) | `MemoryService` (5 layers, shared) |
| Comms | direct calls | `EventBus` pub/sub |
| Agents | registered in code | **plugins** auto-discovered from `kage/plugins/` |
| Improvement | none | **Harness Agent** (benchmark + propose) |
| External AI | none | **Bridge Agents** (OpenCode, OpenClaw) |
| Actions | (v2.1) supervisor executes JSON actions | unchanged — actions still work |

## Migration steps (recommended order)

1. **No-op start.** v2 modules import alongside v1 with zero behavior change.
2. **Adopt the ToolManager** for new agents instead of `ToolRegistry`; the old
   registry remains for the existing supervisor.
3. **Route new multi-agent tasks through the Orchestrator**; keep
   `Supervisor.think()` for single-turn CLI/Discord chat (they coexist).
4. **Publish events** from new code (`bus.publish(...)`) so the Harness and
   future agents can observe activity.
5. **Ship new agents as plugins** under `kage/plugins/` rather than hard-coding
   them into `agents/`.
6. **Wire the Harness** into your CI/benchmark loop to catch regressions.

## Coexistence guarantees

- `Supervisor`, `Registry`, `MemoryStore`, `SessionStore`, tools, workflows,
  the CLI, and the Discord agent are **unchanged**.
- The Orchestrator can use the **same** `AgentRegistry`, so existing agents are
  immediately reachable from v2 flows.
- `__version__` bumped to `3.0.0` to mark the architecture milestone.

## Rollback

Because v2 is purely additive, removing `kage/core/{events,tool_manager,
memory_service,planner,orchestrator,plugins}.py`, `kage/agents/{harness,planner,
bridge,security}/`, `kage/plugins/`, and `benchmarks/` restores v2.1 behavior
exactly.
