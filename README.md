# KAGE OS — CLI AI Operating System for Termux

A decisive, intelligent AI OS inspired by Hermes, OpenCode, OpenClaw, and OpenClaude.

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
