"""cli/repl.py — interactive REPL with slash commands (Phase 3).

Commands:
    /help                        show available commands
    /agents                      list registered agents
    /models                      list configured models
    /providers                   list configured providers
    /config list|get <k>|set <k> <v>
    /secrets list|add <k> <v>|remove <k>
    /workflows                   run the bundled branching demo
    /shell <cmd>                 validate/exec a sandboxed command (dry-run aware)
    /health                      exercise retry/timeout backoff
    /exit                        quit

Batch modes: run_command(line, output="json"|"yaml"|"text", dry_run=...).
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional, Tuple

from .. import __version__
from ..core import config as cfg
from ..core.health import run_with_retry
from ..core.observability import metric_summary, reset as obs_reset
from ..core.result import ToolResult
from ..core import sandbox
from ..core import secrets as secrets_mod
from ..core.workflows.branching import (
    Branch, Retry, Step, Workflow, execute_workflow,
)

# --- theme + completion (polished interface) ---
try:
    from .theme import C, paint, banner as _banner
    from .completer import install_completion, suggestions
    _THEME = True
except Exception:  # noqa: BLE001 — degrade to plain text if theme unavailable
    _THEME = False

    class _C:  # type: ignore
        CYAN = RESET = DIM = GREEN = YELLOW = GRAY = WHITE = ""
    C = _C()  # type: ignore

    def paint(text, color="", bold=False, enabled=None):  # type: ignore
        return text

    def _banner(version="", enabled=None):  # type: ignore
        return f"KAGE OS v{version}"

    def install_completion(commands):  # type: ignore
        return False

    def suggestions(prefix, commands, limit=12):  # type: ignore
        return []

try:
    from .commands import command_names as _command_names
except Exception:  # noqa: BLE001
    def _command_names():  # type: ignore
        return ["/help", "/agents", "/version", "/exit"]

PROMPT_C = "kage❯ "
PROVIDERS = ["openai", "anthropic", "google", "mistral", "groq", "local"]
MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini"],
    "anthropic": ["claude-3-5-sonnet", "claude-3-haiku"],
    "google": ["gemini-1.5-pro", "gemini-1.5-flash"],
    "groq": ["llama-3.1-70b", "llama-3.1-8b"],
    "mistral": ["mistral-large", "mistral-small"],
    "local": ["kage-internal"],
}


def _demo_workflow() -> Workflow:
    return Workflow(
        entry="recall",
        steps=[
            Step(id="recall", name="Recall context", agent="memory", action="memory.recall"),
            Step(id="decide", name="Compose greeting", agent="discord", action="llm.complete",
                 branch=Branch(field="status", equals="ok", then_step="send", else_step="fallback"),
                 retry=Retry(max_attempts=3, base_delay=0.01)),
            Step(id="send", name="Post to Discord", agent="discord", action="discord.send", next=None),
            Step(id="fallback", name="Fallback note", agent="obsidian", action="obsidian.write", next=None),
        ],
    )


# ------------------------------- formatting --------------------------------

def _scalar(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _dump_yaml(obj: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(obj, dict):
        lines: List[str] = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}{k}:")
                lines.append(_dump_yaml(v, indent + 1))
            else:
                lines.append(f"{pad}{k}: {_scalar(v)}")
        return "\n".join(lines)
    if isinstance(obj, list):
        lines = []
        for item in obj:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(_dump_yaml(item, indent + 1))
            else:
                lines.append(f"{pad}- {_scalar(item)}")
        return "\n".join(lines)
    return f"{pad}{_scalar(obj)}"


def format_output(value: Any, output: str = "text") -> str:
    if output == "json":
        return json.dumps(value, indent=2, default=str)
    if output == "yaml":
        try:
            import yaml  # type: ignore
            return yaml.safe_dump(value, sort_keys=False)
        except Exception:
            return _dump_yaml(value)
    return _render_text(value)


def _render_text(value: Any, depth: int = 0) -> str:
    pad = "  " * depth
    if isinstance(value, dict):
        return "\n".join(
            f"{pad}{k}: {_render_text(v, depth + 1) if isinstance(v, (dict, list)) else _scalar(v)}"
            for k, v in value.items()
        )
    if isinstance(value, list):
        return "\n".join(f"{pad}- {_render_text(v, depth + 1) if isinstance(v, (dict, list)) else _scalar(v)}" for v in value)
    return _scalar(value)


# ------------------------------- command core ------------------------------

HELP = {
    "/help": "show this help",
    "/agents": "list registered agents",
    "/models": "list configured models",
    "/providers": "list configured providers",
    "/config list | get <key> | set <key> <value>": "view/edit persisted config",
    "/secrets list | add <key> <value> | remove <key>": "manage secrets (env-only)",
    "/workflows": "run the bundled branching demo workflow",
    "/shell <command>": "validate/exec a sandboxed command",
    "/health": "exercise retry/timeout backoff",
    "/version": "print version",
    "/exit": "quit the REPL",
}


def _split(line: str) -> Tuple[str, List[str]]:
    parts = line.strip().split()
    return (parts[0] if parts else ""), parts[1:]


def cmd_agents() -> Any:
    try:
        from ..core.registry import AgentRegistry  # may pull transport deps
        reg = AgentRegistry()
        return [a.info() for a in getattr(reg, "agents", [])]
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        return {"note": "agent registry unavailable in this environment",
                "error": str(exc), "hint": "install the package with optional deps"}


def cmd_config(args: List[str]) -> Any:
    c = cfg.load_config()
    if not args or args[0] == "list":
        return c.to_dict()
    if args[0] == "get" and len(args) > 1:
        return {args[1]: c.to_dict().get(args[1])}
    if args[0] == "set" and len(args) > 2:
        key, value = args[1], " ".join(args[2:])
        if hasattr(c, key):
            if isinstance(getattr(c, key), bool):
                value = value.lower() in ("1", "true", "yes", "on")
            setattr(c, key, value)
            cfg.save_config(c)
            return {"ok": True, "key": key, "saved": True}
        return {"ok": False, "error": f"unknown config key '{key}'"}
    return {"error": "usage: /config list | get <key> | set <key> <value>"}


def cmd_secrets(args: List[str]) -> Any:
    if not args or args[0] == "list":
        return [s.to_dict() for s in secrets_mod.list_secrets()]
    if args[0] == "add" and len(args) > 2:
        masked = secrets_mod.add_secret(args[1], " ".join(args[2:]))
        return {"ok": True, "key": args[1], "masked": masked}
    if args[0] == "remove" and len(args) > 1:
        return {"ok": secrets_mod.remove_secret(args[1]), "key": args[1]}
    return {"error": "usage: /secrets list | add <key> <value> | remove <key>"}


def cmd_workflows() -> Any:
    wf = _demo_workflow()

    def runner(step: Step, attempt: int) -> ToolResult:
        return ToolResult.success({"step": step.id, "attempt": attempt, "action": step.action})

    return execute_workflow(wf, runner)


def cmd_shell(args: List[str], dry_run: bool) -> Any:
    command = " ".join(args)
    res = sandbox.run(command, dry_run=dry_run)
    return res.to_dict()


def cmd_health() -> Any:
    attempts = {"n": 0}

    def flaky(attempt: int) -> str:
        attempts["n"] = attempt
        if attempt < 2:
            raise RuntimeError("simulated transient failure")
        return "ok"

    res = run_with_retry(flaky, max_attempts=3, base_delay=0.01)
    return {"status": res.status, "attempts": attempts["n"], "durationMs": round(res.durationMs, 2)}


def run_command(line: str, *, output: str = "text", dry_run: bool = False) -> str:
    """Execute one REPL line and return its formatted output."""
    cmd, args = _split(line)
    if not cmd:
        return ""
    if not cmd.startswith("/"):
        return format_output({"echo": line, "note": "use /help to list commands"}, output)

    handler = cmd.lstrip("/").split("/")[0]
    value: Any
    if cmd == "/help":
        value = HELP
    elif cmd == "/version":
        value = {"version": __version__}
    elif cmd == "/agents":
        value = cmd_agents()
    elif cmd == "/models":
        value = MODELS
    elif cmd == "/providers":
        value = PROVIDERS
    elif cmd == "/config":
        value = cmd_config(args)
    elif cmd == "/secrets":
        value = cmd_secrets(args)
    elif cmd == "/workflows":
        value = cmd_workflows()
    elif cmd == "/shell":
        value = cmd_shell(args, dry_run)
    elif cmd == "/health":
        value = cmd_health()
    elif cmd in ("/exit", "/quit"):
        value = {"bye": True}
    else:
        value = {"error": f"unknown command '{cmd}' — try /help"}
    return format_output(value, output)


class REPL:
    """Polished interactive REPL with cyan prompt + slash-command completion."""

    def __init__(self, output: str = "text", dry_run: bool = False) -> None:
        self.output = output
        self.dry_run = dry_run
        obs_reset()

    def banner(self) -> str:
        """Compact banner: ASCII art if theme present, else a one-liner."""
        if _THEME:
            return _banner(version=__version__)
        return f"KAGE OS v{__version__} — type /help for commands."

    def handle(self, line: str) -> Optional[str]:
        line = line.strip()
        if not line:
            return None
        if line in ("/exit", "/quit"):
            return "__exit__"
        return run_command(line, output=self.output, dry_run=self.dry_run)

    def _suggestion_block(self, prefix: str) -> str:
        """Render matching /commands compactly (shown on a bare '/' or filter)."""
        names = suggestions(prefix, _command_names())
        if not names:
            return paint("(no matching commands)", C.GRAY)
        return "\n".join(f"  {paint(n, C.CYAN):<20}" for n in names)

    def loop(self, stream=None) -> None:
        stream = stream or sys.stdin
        # Enable Tab-to-complete for /commands (no-op if readline missing).
        install_completion(_command_names())
        print(self.banner())
        print()
        while True:
            try:
                line = input(paint(PROMPT_C, C.CYAN, bold=True))
            except (EOFError, KeyboardInterrupt):
                print("\n" + paint("bye 👋", C.CYAN))
                break
            stripped = line.strip()
            # bare '/' lists commands; a partial '/x' with no exact match hints.
            if stripped == "/":
                print(self._suggestion_block("/"))
                continue
            out = self.handle(line)
            if out == "__exit__":
                print(paint("bye 👋", C.CYAN))
                break
            if out:
                print(out)


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point: ``kage cli`` / ``python -m kage.cli``.

    Flags: --json, --yaml, --dry-run. With no positional command, drop into
    the REPL; otherwise run a single command and exit (batch mode).
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    output = "text"
    if "--json" in argv:
        output, argv = "json", [a for a in argv if a != "--json"]
    elif "--yaml" in argv:
        output, argv = "yaml", [a for a in argv if a != "--yaml"]
    dry_run = "--dry-run" in argv
    argv = [a for a in argv if a != "--dry-run"]

    if not argv:
        REPL(output=output, dry_run=dry_run).loop()
        return 0

    line = " ".join(argv)
    if not line.startswith("/"):
        line = "/shell " + line if dry_run else "/help"
    print(run_command(line, output=output, dry_run=dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
