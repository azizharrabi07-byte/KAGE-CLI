# KAGE OS — User Guide

A personal AI operating system for the terminal (Termux-first). KAGE is decisive,
modular, secure and efficient.

## 1. Installation

```bash
git clone https://github.com/azizharrabi07-byte/KAGE-CLI.git
cd KAGE-CLI
bash setup.sh                 # creates ~/.kage/, installs deps
pip install -e ./kage
```

## 2. Configuration (first run)

```bash
kage config wizard            # interactive setup
# or set env vars in ~/.kage/.env:
#   DISCORD_BOT_TOKEN=...      (primary interface)
#   LLM_API_KEY=...            (optional, for chat/research)
#   OBSIDIAN_TOKEN=...         (optional, vault)
#   WHATSAPP_BRIDGE_URL=...    (optional, WhatsApp bridge)
```

Secrets are read from the environment ONLY and are never written to logs.

## 3. Running

```bash
kage start                    # start the supervisor daemon
kage status                   # check daemon health
kage run --interface discord  # run Discord transport (primary)
kage chat "remember my name is Daddy"
kage repl                     # interactive REPL
kage agents                   # list registered agents
kage tools                    # list registered tools
kage version
```

## 4. The CLI REPL

Drop in with `python -m kage.cli` or `kage repl`. Slash commands:

| Command | Action |
|---|---|
| `/help` | List commands |
| `/agents` | List registered agents |
| `/models` `/providers` | List models / providers |
| `/config list\|get <k>\|set <k> <v>` | View/edit config |
| `/secrets list\|add <k> <v>\|remove <k>` | Manage secrets |
| `/workflows` | Run the branching demo |
| `/shell <cmd>` | Sandbox-validated command |
| `/health` | Exercise retry/timeout backoff |
| `/exit` | Quit |

Flags for batch mode: `--json`, `--yaml`, `--dry-run`.

## 5. Agents

| Agent | Kind | Role |
|---|---|---|
| Discord | discord | Primary conversational interface |
| Telegram | telegram | Optional/legacy bridge |
| WhatsApp | whatsapp | Message bridge (local Baileys REST) |
| Obsidian | obsidian | Vault read/write/search (Local REST API) |
| System | system | Device health: battery, storage, CPU, memory |
| Meta | meta | Self-upgrade (git pull + tests) and crew reflection |

## 6. Workflows

```bash
kage workflow run examples/workflows/onboarding.json
```

Steps support conditional branching (`when`), per-step retry (`retries`),
and dependencies (`depends_on`). State persists to SQLite so runs resume.

## 7. Security

- Shell commands are validated and sandboxed (allow-list only).
- File paths reject traversal (`../`) and null bytes.
- Secrets are masked in logs automatically.
- Use `/secrets` to manage tokens.

## 8. Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## 9. The OpenCode-style Terminal Interface (v3.1)

`kage repl` launches a polished terminal UI:

```
┌─────────────────────────────────────────────────────────────┐
│   ██╗  ██╗ █████╗ ...   (KAGE ASCII banner)                 │
│   KAGE AI OS v3.1.0 · Terminal AI Operating System          │
│   ⌘ Tab agents  ⌘ Ctrl+P commands  ⌘ Ctrl+F sessions       │
└─────────────────────────────────────────────────────────────┘
```

| Key | Action |
|---|---|
| **Tab** | Agent list panel (running/idle status) |
| **Ctrl+P** | Command palette (all slash commands) |
| **Ctrl+F** | Session list (pins the active session) |
| **Ctrl+L** | Clear screen |
| **Ctrl+C/D** | Quit |

The persistent status line shows `KAGE v3.1.0 · Groq (llama-3.3-70b)` and
`Agents: N · Mem: XXmb · Session: kage-xxx`. Output is colour-coded
(green = success, yellow = warning, red = error); colors auto-disable when piped.

### CLI ↔ Discord parity
Every command lives in the **unified registry** (`kage/cli/commands.py`), so the
Termux REPL and the Discord bot expose identical capabilities:

`/help /agents /plugins /install /remove /harness /tools /config /secrets
/providers /models /search /research /memory /workflow /shell /system /session
/version /exit`

### Plugin management
```bash
kage plugins               # list installed plugins
kage install summarizer    # install a plugin (manifest.yaml)
kage remove summarizer     # remove it
```

### The Harness (continuous improvement)
```bash
kage harness start         # begin monitoring
kage harness run           # run one analyze→propose→report cycle
kage harness status
kage harness stop
```
The Harness benchmarks latency/tokens/success, computes a health score, and
proposes upgrades **for your approval** — never auto-applies them.
