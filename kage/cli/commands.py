"""cli/commands.py — unified slash-command registry (CLI ↔ Discord parity).

Single source of truth for every command so the Termux REPL and the Discord bot
expose identical capabilities. Each command has a name, description, and a
handler(ctx) -> str. The TUI command palette and the help index both read from
``COMMANDS``. New commands added here appear in BOTH interfaces automatically.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .. import __version__
from ..core import config as cfg
from ..core import secrets as secrets_mod
from ..core.health import run_with_retry


@dataclass
class Command:
    name: str
    description: str
    category: str = "general"
    aliases: List[str] = field(default_factory=list)

    def to_palette(self) -> tuple:
        return (self.name, self.description)


# --- harness controller (shared singleton) ---------------------------------
# A tiny in-memory controller so /harness start|stop|status works in the REPL
# and the Discord bot identically, without a long-running thread by default.
@dataclass
class HarnessState:
    running: bool = False
    cycles: int = 0
    last_report: Optional[Dict[str, Any]] = None

    def start(self) -> str:
        if self.running:
            return "Harness already running."
        self.running = True
        return "🟢 Harness started — monitoring latency/tokens/success. Use /harness run to analyze."

    def stop(self) -> str:
        self.running = False
        return "🔴 Harness stopped."

    def status(self) -> str:
        return (f"running={self.running} · cycles={self.cycles} · "
                f"last_score={self.last_report.get('score') if self.last_report else '—'}")

    def run_cycle(self, ctx: Dict[str, Any]) -> str:
        """Run one analyze→propose→report cycle against the latest run(s)."""
        self.cycles += 1
        from ..agents.harness.agent import HarnessAgent
        h = HarnessAgent(); h.wake()
        runs = ctx.get("runs") or [{"agent": "supervisor", "ok": True, "durationMs": 120}]
        bm = h.execute({"op": "benchmark", "agent": "supervisor", "runs": runs})
        prop = h.execute({"op": "propose", "agent": "supervisor",
                          "weaknesses": [] if bm["data"]["success_rate"] == 1.0 else ["flaky results"]})
        self.last_report = {"score": bm["data"]["health"], "success_rate": bm["data"]["success_rate"],
                            "p95": bm["data"]["latency_ms_p95"], "suggestions": prop["data"]["suggestions"]}
        lines = [f"🔬 Harness cycle {self.cycles}",
                 f"  health: {bm['data']['health']}/100 · success {bm['data']['success_rate']:.0%}",
                 f"  p95 latency: {bm['data']['latency_ms_p95']}ms"]
        for s in prop["data"]["suggestions"]:
            lines.append(f"  💡 {s}")
        lines.append("  (proposals require approval — not auto-applied)")
        return "\n".join(lines)


harness = HarnessState()


# --- command table ----------------------------------------------------------
# Handler signature: handler(args: List[str], ctx: Dict) -> str
def _help(args, ctx) -> str:
    return _help_text()


def _version(args, ctx) -> str:
    return f"KAGE AI OS v{__version__}"


def _agents(args, ctx) -> str:
    reg = ctx.get("registry")
    if not reg:
        return "(no registry in context)"
    lines = []
    for a in reg.all_info():
        lines.append(f'{a.get("emoji","🤖")} {a["name"]:<12} {a.get("kind",""):<10} '
                     f'{"awake" if a.get("awake") else "asleep"}')
    return "\n".join(lines) or "(no agents)"


def _plugins(args, ctx) -> str:
    from ..core.plugins import PluginManager
    pm = ctx.get("plugin_manager") or PluginManager()
    installed = pm.list_plugins()
    if not installed:
        return "(no plugins installed)"
    return "\n".join(f"  {p['emoji']} {p['name']} v{p['version']} — {p['description']}" for p in installed)


def _install(args, ctx) -> str:
    from ..core.plugins import PluginManager
    if not args:
        return "usage: /install <plugin-name>"
    pm = ctx.get("plugin_manager") or PluginManager()
    ok = pm.install(args[0])
    return f"✅ installed {args[0]}" if ok else f"❌ plugin '{args[0]}' not found"


def _remove(args, ctx) -> str:
    from ..core.plugins import PluginManager
    if not args:
        return "usage: /remove <plugin-name>"
    pm = ctx.get("plugin_manager") or PluginManager()
    return f"✅ removed {args[0]}" if pm.remove(args[0]) else f"❌ '{args[0]}' not installed"


def _harness(args, ctx) -> str:
    sub = args[0] if args else "status"
    if sub == "start":
        return harness.start()
    if sub == "stop":
        return harness.stop()
    if sub == "run":
        return harness.run_cycle(ctx)
    if sub == "status":
        return harness.status()
    return "usage: /harness start | stop | run | status"


def _providers(args, ctx) -> str:
    return "\n".join(["openai", "anthropic", "google", "groq", "mistral", "local"])


def _models(args, ctx) -> str:
    models = {"groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
              "openai": ["gpt-4o", "gpt-4o-mini"],
              "anthropic": ["claude-3.5-sonnet", "claude-3-haiku"]}
    provider = args[0] if args else "groq"
    return "\n".join(models.get(provider, [f"no models listed for {provider}"]))


def _config(args, ctx) -> str:
    c = cfg.load_config()
    if not args or args[0] == "list":
        return "\n".join(f"  {k} = {v}" for k, v in c.to_dict().items())
    if args[0] == "get" and len(args) > 1:
        return f"{args[1]} = {c.to_dict().get(args[1])}"
    if args[0] == "set" and len(args) > 2:
        key, value = args[1], " ".join(args[2:])
        if hasattr(c, key):
            setattr(c, key, value)
            cfg.save_config(c)
            return f"✅ set {key} = {value}"
        return f"❌ unknown key {key}"
    return "usage: /config list | get <k> | set <k> <v>"


def _secrets(args, ctx) -> str:
    if not args or args[0] == "list":
        return "\n".join(f"  {s.key:<20} {s.masked or '(unset)'} [{s.scope}]" for s in secrets_mod.list_secrets()) or "(none)"
    if args[0] == "add" and len(args) > 2:
        secrets_mod.add_secret(args[1], " ".join(args[2:]))
        return f"✅ secret {args[1]} stored (masked, env-only)"
    if args[0] == "remove" and len(args) > 1:
        return f"✅ removed {args[1]}" if secrets_mod.remove_secret(args[1]) else f"❌ {args[1]} not set"
    return "usage: /secrets list | add <k> <v> | remove <k>"


def _health(args, ctx) -> str:
    """Exercise the retry/timeout backoff path and report a health check."""
    attempts = {"n": 0}

    def flaky(attempt: int) -> str:
        attempts["n"] = attempt
        if attempt < 2:
            raise RuntimeError("simulated transient failure")
        return "ok"

    res = run_with_retry(flaky, max_attempts=3, base_delay=0.01)
    return (f"💚 health: {res.status} (recovered after {attempts['n']} attempts, "
            f"{res.durationMs:.1f}ms) — retry/backoff OK")


def _tools(args, ctx) -> str:
    tools = ctx.get("tool_manager")
    if not tools:
        return "(no tool manager in context)"
    return "\n".join(f"  {t['name']:<20} {t['description']}" for t in tools.describe())


COMMANDS: List[Command] = [
    Command("/help", "show available commands", "core", ["/?"]),
    Command("/agents", "list registered agents", "agents"),
    Command("/plugins", "list installed plugins", "plugins"),
    Command("/install", "install a plugin: /install <name>", "plugins"),
    Command("/remove", "remove a plugin: /remove <name>", "plugins"),
    Command("/harness", "improvement loop: start|stop|run|status", "harness"),
    Command("/tools", "list available tools", "core"),
    Command("/config", "view/edit config: list|get|set", "config"),
    Command("/secrets", "manage secrets: list|add|remove", "config"),
    Command("/providers", "list LLM providers", "config"),
    Command("/models", "list models: /models <provider>", "config"),
    Command("/search", "web search (delegates to research)", "agents"),
    Command("/research", "deep research on a topic", "agents"),
    Command("/memory", "remember a fact: /memory add <k> <v>", "agents"),
    Command("/workflow", "run a workflow file", "workflows"),
    Command("/shell", "run a sandboxed command", "tools"),
    Command("/health", "retry/timeout backoff health check", "tools"),
    Command("/system", "device/system health report", "agents"),
    Command("/session", "session control: new|list|resume", "sessions"),
    Command("/version", "print KAGE version", "core"),
    Command("/exit", "quit the REPL", "core", ["/quit"]),
]

HANDLERS: Dict[str, Callable] = {
    "/help": _help, "/?": _help, "/version": _version, "/agents": _agents,
    "/plugins": _plugins, "/install": _install, "/remove": _remove,
    "/harness": _harness, "/tools": _tools, "/config": _config,
    "/secrets": _secrets, "/providers": _providers, "/models": _models,
    "/health": _health,
}


def _help_text() -> str:
    order = ["core", "agents", "tools", "workflows", "plugins", "harness", "config", "sessions"]
    by_cat: Dict[str, List[Command]] = {}
    for c in COMMANDS:
        by_cat.setdefault(c.category, []).append(c)
    lines = [f"{__version__} — commands:"]
    for cat in order:
        if cat not in by_cat:
            continue
        lines.append(f"  {cat}")
        for c in by_cat[cat]:
            lines.append(f"    {c.name:<13} {c.description}")
    lines.append("  (plain text → sent to the supervisor)")
    return "\n".join(lines)


def palette() -> List[tuple]:
    """All (name, desc) pairs for the command palette."""
    return [c.to_palette() for c in COMMANDS]


def run_slash(line: str, ctx: Dict[str, Any]) -> Optional[str]:
    """Run a /command against a context. Returns None if not a slash command."""
    line = line.strip()
    if not line.startswith("/"):
        return None
    parts = line.split()
    name = parts[0]
    args = parts[1:]
    handler = HANDLERS.get(name)
    if handler is None:
        # some commands fall through to the supervisor (search/research/memory/...)
        if name in {c.name for c in COMMANDS}:
            return None  # supervisor handles them as a message
        return f"unknown command {name!r} — try /help"
    try:
        return handler(args, ctx)
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"
