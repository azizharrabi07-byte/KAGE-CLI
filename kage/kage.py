"""kage/kage.py — the daemon + production CLI for KAGE OS.

Commands:
    kage start [--use-telegram]   start the supervisor daemon (IPC socket)
    kage stop                     stop the daemon
    kage status                   is the daemon alive?
    kage run [--interface IFACE]  run a transport foreground (discord/telegram/cli)
    kage chat "<message>"         one-shot message to the supervisor
    kage repl                     interactive REPL with slash commands
    kage agents                   list registered agents
    kage tools                    list registered tools
    kage config wizard            first-run configuration
    kage workflow run <file.json> run a persisted workflow
    kage version

The daemon owns the supervisor + agents; the CLI talks to it over a Unix domain
socket (see core.ipc). If the daemon isn't running, ``kage chat``/``repl`` fall
back to an in-process supervisor so a single command works out of the box.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from . import __version__
from .core.config import Config, load_config, save_config, wizard
from .core.ipc import IPCClient, IPCServer
from .core.memory import MemoryStore
from .core.registry import AgentRegistry
from .core.security import SecurityPolicy
from .core.session import SessionStore
from .core.supervisor import Supervisor
from .core.tools.base import ToolRegistry
from .core.tools.browser import WebFetchTool, WebSearchTool
from .core.tools.crew import CrewTool
from .core.tools.memory_tool import MemoryTool
from .core.tools.shell import ShellTool

log = logging.getLogger("kage")

PIDFILE = Path("~/.kage/kage.pid").expanduser()


# --- assembly --------------------------------------------------------------

def build_supervisor(cfg: Config) -> Supervisor:
    """Construct the full supervisor with registry, tools, memory, sessions."""
    registry = AgentRegistry()
    # Builtin domain agents (placeholders).
    from .agents.builtin import BUILTIN_AGENTS
    for cls in BUILTIN_AGENTS:
        registry.register(cls)
    # Transports are registered lazily (heavy deps); they wake on demand.
    try:
        from .agents.discord.agent import DiscordAgent
        registry.register(DiscordAgent, config={"token": cfg.discord_bot_token})
    except Exception:  # noqa: BLE001
        pass
    if cfg.use_telegram:
        try:
            from .agents.telegram.agent import TelegramAgent
            registry.register(TelegramAgent, config={"token": cfg.telegram_bot_token})
        except Exception:  # noqa: BLE001
            pass

    memory = MemoryStore()
    sessions = SessionStore()
    tools = ToolRegistry()
    for t in (WebFetchTool(), WebSearchTool(), ShellTool(), MemoryTool(memory), CrewTool(registry)):
        tools.register(t)
    security = SecurityPolicy()

    # Bridge to the existing arena-handoff LLM brain (core.brain.Brain) if it is
    # importable. This reuses your already-configured Groq/Gemini/OpenRouter keys
    # for open chat. If absent, the supervisor falls back to its rule-based reply.
    llm = _build_llm_bridge()

    return Supervisor(
        registry=registry, memory_store=memory, session_store=sessions,
        tools=tools, security=security,
        config=Config().__dict__ | {
            "default_user": cfg.default_user,
            "root": os.environ.get("KAGE_ROOT", ""),
            "allow_destructive": os.environ.get(
                "KAGE_ALLOW_DESTRUCTIVE", "").lower() in ("1", "true", "yes"),
        },
        llm=llm,
    )


def _build_llm_bridge():
    """Return a callable llm(message, context)->str using core.brain.Brain, or None."""
    import os
    try:
        # core/ here is the arena-handoff core (sibling of the kage/ package).
        from core.brain import Brain  # type: ignore
    except Exception:  # noqa: BLE001 — brain not importable; rule-based fallback
        return None
    api_key = os.environ.get("KAGE_LLM_API_KEY", "")
    if not api_key:
        return None
    try:
        provider = os.environ.get("KAGE_LLM_PROVIDER", "groq")
        model = os.environ.get("KAGE_LLM_MODEL") or None
        brain = Brain(provider=provider, api_key=api_key, model=model)
    except Exception:  # noqa: BLE001
        return None

    def _llm(message: str, context: str = "") -> str:
        try:
            return brain.think(message, session_context=context)
        except Exception:  # noqa: BLE001
            return ""

    return _llm


# --- IPC handler -----------------------------------------------------------

def make_ipc_handler(supervisor: Supervisor, sessions: SessionStore):
    def handler(req: Dict[str, Any]) -> Dict[str, Any]:
        kind = req.get("type")
        uid = req.get("user_id") or supervisor.default_user
        if kind == "chat":
            resp = supervisor.think(req.get("message", ""), user_id=uid)
            sid = sessions.active(uid) or sessions.create(uid, platform="ipc")
            sessions.add_message(sid, "user", req.get("message", ""))
            sessions.add_message(sid, resp.agent, resp.text)
            return {"ok": True, "response": resp.to_dict(), "session_id": sid}
        if kind == "agents":
            return {"ok": True, "agents": supervisor.registry.all_info()}
        if kind == "tools":
            return {"ok": True, "tools": supervisor.tools.describe_all()}
        if kind == "ping":
            return {"ok": True, "version": __version__}
        return {"ok": False, "error": f"unknown request type: {kind}"}

    return handler


# --- daemon control --------------------------------------------------------

def daemon_start(cfg: Config, use_telegram: bool = False) -> int:
    if PIDFILE.exists() and _pid_alive(int(PIDFILE.read_text().strip())):
        print(f"kage daemon already running (pid {PIDFILE.read_text().strip()})")
        return 0
    # Re-launch self in daemon mode with a new session (nohup-style).
    logf = open(Path("~/.kage/kage.log").expanduser(), "ab", buffering=0)
    proc = subprocess.Popen(
        [sys.executable, "-m", "kage.kage", "daemon", "--use-telegram" if use_telegram else ""],
        stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        start_new_session=True, cwd=str(Path.cwd()),
    )
    # Filter empty arg
    PIDFILE.write_text(str(proc.pid))
    time.sleep(0.6)
    print(f"kage daemon started (pid {proc.pid}). Log: ~/.kage/kage.log")
    return 0


def daemon_stop() -> int:
    if not PIDFILE.exists():
        print("kage daemon not running")
        return 1
    pid = int(PIDFILE.read_text().strip())
    if not _pid_alive(pid):
        PIDFILE.unlink(missing_ok=True)
        print("kage daemon not running (stale pid)")
        return 1
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        PIDFILE.unlink(missing_ok=True)
        return 1
    for _ in range(10):
        time.sleep(0.3)
        if not _pid_alive(pid):
            break
    if _pid_alive(pid):
        os.kill(pid, signal.SIGKILL)
    PIDFILE.unlink(missing_ok=True)
    print(f"kage daemon stopped (pid {pid})")
    return 0


def daemon_status(cfg: Config) -> int:
    client = IPCClient(cfg.socket_path)
    if not client.is_alive() and not (PIDFILE.exists() and _pid_alive(int(PIDFILE.read_text().strip()))):
        print("kage daemon: stopped")
        return 1
    res = client.request({"type": "ping"})
    if res.get("ok"):
        print(f"kage daemon: running (v{res.get('version', '?')})")
        return 0
    print("kage daemon: not responding")
    return 1


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def run_daemon(cfg: Config, use_telegram: bool) -> int:
    """The actual daemon process: supervisor + IPC server (+ transports)."""
    logging.basicConfig(level=cfg.log_level, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    supervisor = build_supervisor(cfg)
    ipc = IPCServer(cfg.socket_path, make_ipc_handler(supervisor, supervisor.sessions))

    # Background transports wake their agents in threads.
    import threading
    ifaces = ["discord"]
    if use_telegram:
        ifaces.append("telegram")
    for iface in ifaces:
        agent = supervisor.registry.get(iface)
        if agent is None:
            log.warning("interface %s not available", iface)
            continue

        def _run(a=agent):  # type: ignore[no-untyped-def]
            try:
                a.wake()
                a.execute()
            except Exception as exc:  # noqa: BLE001
                log.error("interface %s crashed: %s", a.name, exc)

        threading.Thread(target=_run, daemon=True).start()

    def _shutdown(*_: Any) -> None:
        log.info("shutting down daemon")
        ipc.stop()
        for name in supervisor.registry.list():
            try:
                supervisor.registry.sleep(name)
            except Exception:  # noqa: BLE001
                pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    ipc.serve_forever()
    return 0


# --- in-process fallback ---------------------------------------------------

def local_supervisor() -> Supervisor:
    return build_supervisor(load_config())


# --- REPL ------------------------------------------------------------------

SLASH_HELP = {
    "/help": "show commands", "/agents": "list agents", "/tools": "list tools",
    "/memory": "remember/recall", "/system": "health", "/session": "sessions",
    "/quit": "exit",
}


def repl(supervisor: Supervisor) -> int:
    """Launch the OpenCode-style TUI (banner, status line, Tab/Ctrl+P/Ctrl+F)."""
    from .core.plugins import PluginManager
    try:
        from .cli.tui import KageTUI
    except Exception:  # noqa: BLE001 — fall back to plain loop if TUI unavailable
        return _repl_plain(supervisor)
    pm = PluginManager(registry=supervisor.registry, plugin_root="kage/plugins")
    try:
        pm.install_all()
    except Exception:  # noqa: BLE001
        pass
    tui = KageTUI(supervisor=supervisor, registry=supervisor.registry,
                  tool_manager=supervisor.tools, plugin_manager=pm,
                  sessions=getattr(supervisor, "sessions", None))
    return tui.run()


def _repl_plain(supervisor: Supervisor) -> int:
    """Minimal line-based fallback REPL (kept for environments without the TUI)."""
    uid = supervisor.default_user
    print(f"KAGE OS v{__version__} — /help, /quit")
    while True:
        try:
            line = input("kage> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); return 0
        if not line:
            continue
        if line in ("/quit", "/exit"):
            return 0
        msg = line[1:] if line.startswith("/") else line
        resp = supervisor.think(msg, user_id=uid)
        print(f"{getattr(resp, 'agent', 'Kage')} · {resp.intent}\n{resp.text}\n")


# --- argparse main ---------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    cfg = load_config()
    parser = argparse.ArgumentParser(prog="kage", description="KAGE OS — personal AI OS for the terminal")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    parser.add_argument("--dry-run", action="store_true", help="plan without side effects")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="show version")
    sub.add_parser("start", help="start the daemon").add_argument("--use-telegram", action="store_true")
    sub.add_parser("stop", help="stop the daemon")
    sub.add_parser("status", help="daemon status")
    sub.add_parser("repl", help="interactive REPL")

    p_run = sub.add_parser("run", help="run a transport in the foreground")
    p_run.add_argument("--interface", default="discord", choices=["discord", "telegram", "cli"])

    p_chat = sub.add_parser("chat", help="one-shot message")
    p_chat.add_argument("message")
    p_chat.add_argument("--json", action="store_true", help="emit JSON output")
    p_chat.add_argument("--dry-run", action="store_true", help="plan without side effects")

    sub.add_parser("agents", help="list agents")
    sub.add_parser("tools", help="list tools")

    p_cfg = sub.add_parser("config", help="configuration")
    p_cfg.add_argument("action", choices=["wizard", "show"])

    p_wf = sub.add_parser("workflow", help="workflow engine")
    p_wf.add_argument("action", choices=["run"])
    p_wf.add_argument("file")

    sub.add_parser("daemon", help="(internal) run the daemon process").add_argument(
        "--use-telegram", action="store_true")

    # --- v3 plugin / harness CLI (Phase 1 / 5) ---
    p_install = sub.add_parser("install", help="install a plugin")
    p_install.add_argument("name")
    p_remove = sub.add_parser("remove", help="remove a plugin")
    p_remove.add_argument("name")
    sub.add_parser("plugins", help="list installed plugins")
    p_harness = sub.add_parser("harness", help="improvement loop control")
    p_harness.add_argument("action", choices=["start", "stop", "run", "status"])

    args = parser.parse_args(argv)
    args_dict = vars(args)

    if args.cmd == "version":
        print(f"kage {__version__}")
        return 0
    if args.cmd == "daemon":
        return run_daemon(cfg, args_dict.get("use_telegram", False))
    if args.cmd == "start":
        return daemon_start(cfg, args_dict.get("use_telegram", False))
    if args.cmd == "stop":
        return daemon_stop()
    if args.cmd == "status":
        return daemon_status(cfg)

    if args.cmd == "config":
        if args.action == "wizard":
            c = wizard(interactive=True)
            print(f"config saved to {Config.path()}")
            return 0
        print(json.dumps(cfg.to_dict(), indent=2))
        return 0

    if args.cmd == "agents":
        client = IPCClient(cfg.socket_path)
        res = client.request({"type": "agents"})
        if not res.get("ok"):
            res = {"agents": local_supervisor().registry.all_info()}
        for a in res["agents"]:
            print(f'  {a["emoji"]} {a["name"]:<10} {a["kind"]}')
        return 0

    if args.cmd == "tools":
        sup = local_supervisor()
        for t in sup.tools.describe_all():
            print(f'  {t["name"]:<14} {t["description"]}')
        return 0

    if args.cmd == "workflow":
        from .core.workflows.engine import WorkflowEngine
        engine = WorkflowEngine()
        info = engine.load(args.file)
        sup = local_supervisor()

        def executor(step):  # type: ignore[no-untyped-def]
            action = step["action"]
            if action == "tool":
                # step["args"] = {"name": <tool>, "args": {<tool args>}}
                spec = step["args"]
                return sup.run_tool(spec.get("name", ""), spec.get("args", {}))
            if action == "think":
                r = sup.think(step["args"].get("message", ""))
                return {"ok": r.ok, "text": r.text}
            return {"ok": False, "error": f"unknown action {action}"}

        result = engine.run(info["workflow_id"], executor)
        print(json.dumps(result, indent=2))
        return 0

    if args.cmd == "run":
        iface = args.interface
        sup = local_supervisor()
        agent = sup.registry.get(iface)
        if agent is None:
            print(f"interface {iface} not available")
            return 1
        agent.wake()
        agent.execute()
        return 0

    if args.cmd == "chat":
        if args.dry_run:
            print(f"[dry-run] would send: {args.message}")
            return 0
        client = IPCClient(cfg.socket_path)
        res = client.request({"type": "chat", "user_id": cfg.default_user, "message": args.message})
        if not res.get("ok"):
            # in-process fallback
            resp = local_supervisor().think(args.message, user_id=cfg.default_user)
            res = {"response": resp.to_dict()}
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            r = res["response"]
            print(f"{r['agent']} · {r['intent']}\n{r['text']}")
        return 0

    if args.cmd in ("install", "remove", "plugins"):
        from .core.plugins import PluginManager
        sup = local_supervisor()
        pm = PluginManager(registry=sup.registry, plugin_root="kage/plugins")
        pm.install_all()
        if args.cmd == "plugins":
            for pl in pm.list_plugins():
                print(f'  {pl["emoji"]} {pl["name"]} v{pl["version"]} — {pl["description"]}')
            return 0
        if args.cmd == "install":
            print(f"installed {args.name}" if pm.install(args.name) else f"plugin '{args.name}' not found")
            return 0
        print(f"removed {args.name}" if pm.remove(args.name) else f"'{args.name}' not installed")
        return 0

    if args.cmd == "harness":
        from .cli.commands import harness
        if args.action == "start":
            print(harness.start())
        elif args.action == "stop":
            print(harness.stop())
        elif args.action == "status":
            print(harness.status())
        else:
            print(harness.run_cycle({"runs": [{"agent": "supervisor", "ok": True, "durationMs": 120}]}))
        return 0

    if args.cmd == "repl":
        return repl(local_supervisor())

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
