# KAGE OS v2 — Master Architecture

> KAGE is not an AI assistant. It is an **AI Operating System**: a conductor that
> understands intent, plans, selects agents on demand, coordinates them, merges
> outputs, stores memory, and terminates agents — with intelligence emerging
> from **orchestration**, not from one giant prompt.

## Design principles

1. **Modular** — every agent has one responsibility; none is a monolith.
2. **Plugin-based** — agents are installable plugins discovered from disk.
3. **Event-driven** — agents communicate through an event bus, never directly.
4. **On-demand runtime** — only the Orchestrator is always-on; agents start when
   needed and terminate after their unit of work (low RAM/CPU, phone-friendly).
5. **Bridges, not clones** — mature external systems (OpenCode, OpenClaw,
   LangGraph, CrewAI, AutoGen, OpenHands) are integrated behind Bridge Agents,
   never reimplemented.
6. **Continuously improving** — the **Harness Agent** evaluates every run,
   benchmarks candidates, and proposes (never auto-deploys) upgrades.
7. **Local-first / dependency-light** — core is Python stdlib only.

## Layer diagram

```
                         ┌──────────────┐
   user (CLI / Discord)  │  Transports  │
                         └──────┬───────┘
                                │
                  ┌─────────────▼──────────────┐
                  │      Orchestrator (kernel) │  ← always-on conductor
                  │  receive→plan→select→run   │
                  │  →merge→memory→terminate   │
                  └─┬────────┬────────┬────┬───┘
            ┌───────┘        │        │    └────────┐
            ▼                ▼        ▼             ▼
       ┌─────────┐    ┌──────────┐ ┌────────┐ ┌──────────┐
       │ Planner │    │Event Bus │ │ Memory │ │  Tools   │
       │         │    │ pub/sub  │ │Service │ │ Manager  │
       └─────────┘    └────┬─────┘ └────────┘ └──────────┘
                           │
        ┌──────┬───────┬───┴────┬────────┬──────────┐
        ▼      ▼       ▼        ▼        ▼          ▼
     Agents (on demand, plugin-discovered)
     planner · research · memory · system · security · harness
     opencode-bridge · openclaw-bridge · summarizer · …
```

## The pillars (implemented)

| Pillar | Module | Responsibility |
|---|---|---|
| **Orchestrator** | `core/orchestrator.py` | The conductor: plans, starts agents on demand, merges results, terminates them. |
| **Event Bus** | `core/events.py` | Pub/sub with hierarchical wildcard topics; decouples all agents. |
| **Tool Manager** | `core/tool_manager.py` | Single gateway to all tools (fs/git/terminal/browser/memory/search). Agents never call tools directly. |
| **Memory Service** | `core/memory_service.py` | 5 layers (session/project/user/knowledge/longterm) behind one interface. |
| **Planner** | `core/planner.py` | Decomposes a goal into an `ExecutionPlan` (rule-based, LLM-enrichable). |
| **Plugins** | `core/plugins.py` | Discovers `manifest.yaml` plugins, lazily registers their agents. |
| **Harness Agent** | `agents/harness/` | Flagship continuous-improvement: evaluate, benchmark, compare, propose (never deploy). |
| **Bridge Agents** | `agents/bridge/` | `BridgeAgent` base + OpenCode/OpenClaw bridges; thin adapters, no duplicated reasoning. |

## Runtime flow (the on-demand loop)

```
receive task → publish(task.received)
            → Planner.plan() → publish(task.planned)
            → for each step:
                 start agent (lazy) → execute → ToolResult
                 publish(agent.completed)
                 store session memory
                 terminate agent (sleep)        ← frees resources
            → merge results → publish(task.completed)
            → Harness.evaluate() → benchmark → propose upgrades
```

## Agent contracts

Every agent subclasses `BaseAgent` and implements `wake() / execute(task) / sleep()`.
`execute` returns a structured dict: `{status, data, error}` — same envelope
the orchestrator and Harness consume.

## External integrations (bridges)

```
User → KAGE → OpenCode Bridge → OpenCode → Result → KAGE
User → KAGE → OpenClaw Bridge → OpenClaw → Result → KAGE
```

Bridge agents translate KAGE's task into the external system's CLI/HTTP contract
and translate the response back. They degrade gracefully (structured error) when
the external binary is absent, so the OS never crashes on a missing tool.

## Continuous improvement (Harness)

The Harness Agent is the flagship. It never solves user tasks — it improves
*other* agents:

1. **evaluate** — scores a finished run (failures, coverage).
2. **benchmark** — runs an agent N times, measures latency/p95/variance, computes a weighted **health** score (success 40 / latency 25 / stability 20 / prompt 15).
3. **compare** — baseline vs candidate; recommends a winner.
4. **propose** — generates targeted improvement suggestions, **always with `requires_approval`** — KAGE decides whether to accept the upgrade.

This creates a safe, continuously improving ecosystem.

## Extending KAGE

Add an agent as a **plugin** (see `kage/plugins/summarizer/` for a full example):

```
kage/plugins/<name>/
  manifest.yaml      name, version, agent_class, tools, keywords
  system_prompt.md   agent persona
  agent.py           <Name>Agent(BaseAgent)
  workflow.py        optional workflow definition
  tools.py           optional tool wiring
  tests/             self-tests
  docs/              plugin docs
```

KAGE auto-discovers and lazily registers plugins — extend without touching core.
