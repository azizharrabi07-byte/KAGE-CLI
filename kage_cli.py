#!/usr/bin/env python3
import sys
import uuid
import datetime

from core.context_manager import ContextManager, KAGE_HOME
from core.brain import Brain


def main():
    ctx = ContextManager().load_all()
    brain = Brain(ctx)

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: kage <command> [args]")
        print("  kage chat \"<prompt>\"   Interact with Kage")
        print("  kage status            Check system status")
        print("  kage init              Initialize KAGE OS structure")
        return

    command = sys.argv[1]

    if command == "init":
        _init_structure()
        print("KAGE OS initialized at", KAGE_HOME)
        return

    if command == "status":
        _show_status(ctx)
        return

    if command == "chat":
        user_prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not user_prompt:
            print("Enter your prompt:")
            user_prompt = sys.stdin.readline().strip()
        session_id = str(uuid.uuid4())[:8]
        system_prompt = brain.build_system_prompt(user_prompt, session_id)
        token_count = len(system_prompt.split())
        print(f"[Kage] Session: {session_id} | Prompt tokens: ~{token_count}")
        print(f"[Kage] System prompt built from levels: ", end="")
        levels = ["L1"]
        if ctx._identity_user:
            levels.append("L1(user)")
        if ctx._skills_manifest.get("skills"):
            levels.append("L2(skills)")
        print("+".join(levels))
        print()
        print(system_prompt)
        print()
        print(f"[Kage] Ready. Lazy context would trigger on: remember, earlier, history, continue, workflow, pipeline, notes, memories, obsidian")
        return

    print(f"Unknown command: {command}")


def _init_structure():
    dirs = ["identity", "config", "core", "sessions", "workflows", "long_term"]
    for d in dirs:
        (KAGE_HOME / d).mkdir(parents=True, exist_ok=True)
    readme = KAGE_HOME / "README.md"
    if not readme.exists():
        readme.write_text("# KAGE OS\nTiered Memory Architecture\n")


def _show_status(ctx):
    print("KAGE OS Status")
    print("=" * 40)
    print(f"Home:     {KAGE_HOME}")
    print(f"Identity: agent={bool(ctx._identity_agent)} user={bool(ctx._identity_user)}")
    print(f"Config:   skills={len(ctx._skills_manifest.get('skills', []))} items")
    print(f"Token:    ~{ctx.default_context_token_estimate} (L1+L2)")
    sessions = list((KAGE_HOME / "sessions").glob("*.json")) if (KAGE_HOME / "sessions").exists() else []
    print(f"Sessions: {len(sessions)} on disk (lazy-loaded)")
    workflows = list((KAGE_HOME / "workflows").glob("*.json")) if (KAGE_HOME / "workflows").exists() else []
    print(f"Workflows: {len(workflows)} on disk (lazy-loaded)")


if __name__ == "__main__":
    main()
