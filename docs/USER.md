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
