# AGENTS.md — the crew manifest (Hermes-style).

KAGE OS is a multi-agent system supervised by **Kage**. Each agent owns a
domain and implements `wake()` → `execute()` → `sleep()`.

## Supervisor
- **Kage** 🥷 — the brain. Parses intent, routes work, synthesizes replies.
  Transport-agnostic; never talks to the outside world directly.

## Domain agents
| Agent | Kind | Owns | Status |
| --- | --- | --- | --- |
| **Whiz** 🌐 | web | web.search, web.fetch | routes from supervisor |
| **Sage** 🔬 | research | research.run | routes from supervisor |
| **Mira** 🧠 | memory | memory.recall/add | core memory store |
| **Sentinel** 🛡️ | system | system.report | host health |
| **Vault** 📓 | obsidian | notes, links | placeholder |
| **Relay** 💬 | whatsapp | WA bridge | placeholder |
| **Meta** 🪞 | meta | self-reflection | placeholder |

## Transport agents
- **Discord** 🎮 — PRIMARY interface. `/kage`, `/kage-agents`, `/kage-memory`,
  `/kage-search`, `/kage-research`, `/kage-session`.
- **Telegram** ✈️ — OPTIONAL / deprecated. Same supervisor routing.

## Adding an agent
1. Subclass `kage.core.base_agent.BaseAgent`.
2. Set `name`, `kind`, implement `wake/execute/sleep`.
3. Register in `kage.kage.build_supervisor` (or via registry discovery).

## Adding a tool
1. Subclass `kage.core.tools.base.Tool`, set `meta` (schema/permissions).
2. Register in `build_supervisor`. The supervisor gates it through security.
