# KAGE OS — CLI AI Operating System for Termux

A decisive, intelligent AI OS inspired by Hermes, OpenCode, OpenClaw, and OpenClaude.

> ## ✨ New: Supervisor + Discord (`supervisor-discord` branch)
> The `kage/` package adds a **supervisor daemon + multi-agent core + Discord
> (primary interface)** on top of this foundation. Your existing `core/brain.py`,
> memory, sessions, and Telegram bot are untouched.
>
> ```bash
> pip install -e ./kage && pip install -r requirements.txt
> kage chat "remember my name is Daddy"
> kage run --interface discord   # primary UI
> ```
>
> 👉 Full details: **[`kage/SUPERVISOR.md`](kage/SUPERVISOR.md)**
>
> Discord is now primary; Telegram is optional/deprecated.

## Features

- Layered prompt system (Hermes‑style: SOUL → AGENTS → MEMORY → USER → Dynamic)
- Deep research with configurable depth (1=quick, 3+=deep synthesis)
- Memory management (core JSON + markdown files with add/replace/remove tools)
- Session management (SQLite with /new, /resume, /list, /delete)
- Telegram bot interface with action execution
- Robust browser with DuckDuckGo redirect handling
- Post‑processing (single action extraction, malformed JSON cleanup)

## Quick Start

1. Clone and enter the directory.
2. Run `bash setup.sh`
3. Create `.env` from `.env.example` and fill in your tokens.
4. Run `python kage_cli.py start`

## Commands

- `/new [title]` — Start new session
- `/resume <id>` — Resume session
- `/list` — List sessions
- `/info` — Show active session
- `/delete <id>` — Delete session

## License

MIT
