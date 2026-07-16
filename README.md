# KAGE OS — Personal AI Agent System

A modular CLI-based AI operating system for your phone (Termux/Android).

## Architecture

- **core/** — brain (LLM wrapper), memory (SQLite), permissions, scheduler
- **agents/** — WhatsApp (Baileys bridge), Obsidian (REST API), System (termux-api), Meta (self-upgrade)
- **skills/** — Shared utilities
- **kage.py** — Supervisor daemon
- **kage_cli.py** — User CLI

## Install

```bash
cd ~
tar xzf /sdcard/kage-os.tar.gz
cd kage-os
bash setup.sh
```

## Usage

```bash
kage status              # System status
kage health              # Phone health (battery/storage/CPU)
kage agent list          # List all agents
kage agent create <name> # Create new agent
kage chat "hello"        # Chat with Kage
kage trace list          # Show recent traces
```
