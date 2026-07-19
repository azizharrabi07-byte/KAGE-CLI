# KAGE OS — Supervisor + Discord (Phase 1 & 2)

This adds a **supervisor daemon + multi-agent core + Discord primary interface**
on top of the existing `arena-handoff` foundation (your `core/brain.py` LLM brain,
memory, sessions, and Telegram bot stay **untouched and working**).

The new code lives in the **`kage/`** package. It reuses your configured LLM keys
(`KAGE_LLM_*` / Groq / Gemini / OpenRouter) via a bridge to `core.brain.Brain`.

> Discord is now the **primary** interface. Telegram remains optional/deprecated.

## What's new

```
kage/
├── kage.py                # daemon + CLI (start/stop/status/chat/repl/...)
├── core/
│   ├── supervisor.py      # the brain: intent → agent → structured response
│   ├── base_agent.py      # wake / execute / sleep agent interface
│   ├── registry.py        # lazy agent registry + lifecycle control
│   ├── ipc.py             # Unix-domain-socket daemon protocol
│   ├── config.py          # loading + first-run wizard
│   ├── session.py         # SQLite sessions
│   ├── memory.py          # long-term memory (JSON + Markdown)
│   ├── security.py        # secrets, permissions, sandbox, validation
│   ├── cache.py           # disk cache with TTL
│   ├── tools/             # browser, shell, memory, crew (structured output)
│   ├── integrations/      # retry / timeout / health / auto-reconnect
│   └── workflows/         # persisted multi-step workflow engine
├── agents/
│   ├── discord/agent.py   # PRIMARY interface (/kage slash commands)
│   ├── telegram/agent.py  # optional / deprecated
│   └── builtin.py         # WhatsApp, Obsidian, System, Meta (placeholders)
├── tests/                 # supervisor + tools tests (run without pytest)
├── SOUL.md  AGENTS.md     # Hermes-style prompt layers
├── examples/research.json
├── pyproject.toml         # installs the `kage` command
└── requirements.txt
```

## Install

```bash
pip install -e ./kage        # registers the `kage` command
pip install -r requirements.txt   # adds discord.py
cp .env.example .env         # add DISCORD_BOT_TOKEN (+ your KAGE_LLM_* keys)
kage config wizard           # optional first-run setup
```

## Quick start

```bash
# One-shot (works with no daemon — in-process supervisor)
kage chat "remember my name is Daddy"
kage chat "what is my name?"          # → Daddy (from memory)
kage chat "research AI trends"        # → Sage
kage agents
kage tools
kage repl                             # interactive (/help, /agents, /tools)

# Supervisor daemon (one warm process, IPC socket)
kage start
kage status
kage stop

# Discord (primary UI) in the foreground
kage run --interface discord

# Workflows
kage workflow run kage/examples/research.json
```

Global flags: `--json` (machine output), `--dry-run` (plan without side effects).

## Discord slash commands

`/kage <msg>`, `/kage-agents`, `/kage-memory <key> <value>`,
`/kage-search <q>`, `/kage-research <q>`, `/kage-session <new|list|resume>`.

Enable the **Message Content** privileged intent in the Discord Developer Portal.

## LLM bridge

`kage/kage.py:_build_llm_bridge()` imports your `core.brain.Brain` and wires it
into the supervisor for open chat. Set `KAGE_LLM_API_KEY` / `KAGE_LLM_PROVIDER`
(as you already do). If absent, the supervisor uses its rule-based fallback.

## Tests

```bash
python kage/tests/test_supervisor.py    # 5 tests
python kage/tests/test_tools.py         # 4 tests
```

## Relationship to the foundation

| Existing (untouched) | New (this package) |
| --- | --- |
| `core/brain.py` (LLM) | reuses it via the bridge for chat |
| `core/memory.py`, `core/session_manager.py` | `kage/core/memory.py`, `session.py` (supervisor's own stores) |
| `agents/telegram/` | optional/deprecated; Discord is primary |
| `kage_cli.py` | still works; `kage` is the new supervisor CLI |

Nothing existing is removed or broken. You can run the old `python kage_cli.py`
and the new `kage` side by side.
