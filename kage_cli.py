#!/usr/bin/env python3
"""
kage_cli.py — OpenCode-Style Interactive REPL & Terminal CLI for KAGE OS in Termux.
Supports slash commands (/help, /models, /providers, /config), dynamic config switching,
up-arrow command history via readline, ANSI color formatting, and standardized exit codes.

Subcommands:
  kage                         (Start interactive terminal REPL)
  kage interactive             (Start interactive terminal REPL)
  kage chat "message"          (Send prompt to Kage AI brain)
  kage status                  (Show supervisor and daemon status)
  kage health                  (Check battery, storage, CPU telemetry)
  kage logs [--follow/-f]      (Show last 50 lines or stream daemon log)
  kage agent list|wake|create  (Manage domain agents)
  kage trace list|show         (View trace execution logs)
  kage schedule list|add|delete(Manage automated cron jobs)
  kage test whatsapp           (Run end-to-end WhatsApp bridge check)
  kage daemon start|stop|status(Control background supervisor process)
"""

import argparse
import json
import os
import readline
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.brain import PROVIDER_MODELS, _load_config

KAGE_DIR = Path(__file__).parent
PYTHON = sys.executable
SOCKET_FILE = Path.home() / ".kage" / "kage.sock"
HISTORY_FILE = Path.home() / ".kage" / "history"

# ANSI Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_CYAN = "\033[96m"
C_DIM = "\033[90m"

ASCII_BANNER = f"""{C_BOLD}┌──────────────────────────────────────────────────────────────┐
│  ███▄▄▄▄   ▄████████  ▄████████    ▄████████  ▄██████▄       │
│  ███▀▀▀██▄ ███    ███ ███    ███   ███    ███ ███    ███     │
│  ███   ███ ███    █▀  ███    █▀    ███    █▀  ███    █▀      │
│  ███   ███ ███       ▄███▄▄▄      ▄███▄▄▄     ███    ███     │
│  ███   ███ ███      ▀▀███▀▀▀     ▀▀███▀▀▀     ███    ███     │
│  ███   ███ ███    █▄  ███    █▄    ███    █▄  ███    █▄      │
│  ███   ███ ███    ███ ███    ███   ███    ███ ███    ███     │
│   ▀█   █▀  ████████▀  ██████████   ██████████  ▀██████▀      │
│                                                              │
│  KAGE OS Phase 3 • OpenCode Terminal Shell for Termux        │
│  Type /help for slash commands or enter prompt to chat.      │
└──────────────────────────────────────────────────────────────┘{C_RESET}"""


def run_kage(command: str, args: dict = None) -> dict:
    """Send command payload to daemon IPC Unix socket or execute locally as fallback."""
    args = args or {}
    cmd_payload = json.dumps({"command": command, "args": args})

    if SOCKET_FILE.exists():
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(60.0)
            client.connect(str(SOCKET_FILE))
            client.sendall(cmd_payload.encode("utf-8") + b"\n")

            data = b""
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                data += chunk
                if data.endswith(b"\n"):
                    break
            client.close()
            if data:
                return json.loads(data.decode("utf-8").strip())
        except Exception:
            pass

    try:
        result = subprocess.run(
            [PYTHON, str(KAGE_DIR / "kage.py"), command, json.dumps(args)],
            capture_output=True, text=True, timeout=60,
            cwd=str(KAGE_DIR),
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        else:
            return {"status": "error", "output": result.stderr.strip() or "No response from supervisor"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "output": "Command timed out"}
    except json.JSONDecodeError:
        return {"status": "error", "output": result.stdout.strip() or result.stderr.strip()}
    except Exception as e:
        return {"status": "error", "output": str(e)}


# --- CONFIG MUTATION HELPERS ---

def _load_toml_file(filepath: Path) -> Dict:
    """Load TOML file via toml package or built-in parser."""
    try:
        import toml
        return toml.load(filepath)
    except ImportError:
        data = {}
        current_sec = None
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        current_sec = line[1:-1]
                        if current_sec not in data:
                            data[current_sec] = {}
                    elif "=" in line and current_sec:
                        k, _, val = line.partition("=")
                        data[current_sec][k.strip()] = val.strip().strip('"\'')
        return data


def _write_toml_file(filepath: Path, data: Dict) -> bool:
    """Write TOML dictionary structure safely to disk."""
    try:
        import toml
        with open(filepath, "w", encoding="utf-8") as f:
            toml.dump(data, f)
        return True
    except ImportError:
        lines = []
        for sec, items in data.items():
            lines.append(f"\n[{sec}]")
            if isinstance(items, dict):
                for k, v in items.items():
                    if isinstance(v, bool):
                        v_str = "true" if v else "false"
                    elif isinstance(v, (int, float)):
                        v_str = str(v)
                    elif isinstance(v, (list, dict)):
                        v_str = json.dumps(v)
                    else:
                        v_str = f'"{v}"'
                    lines.append(f"{k} = {v_str}")
            lines.append("")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines).strip() + "\n")
        return True


def set_config_key(key_path: str, value: str) -> bool:
    """Set config key (e.g. llm.model, llm.provider, whatsapp.test_number) in config files."""
    if "." not in key_path:
        print(f"{C_RED}Error: Key must be in format 'section.key' e.g. 'llm.provider' or 'llm.model'{C_RESET}")
        return False

    section, _, key = key_path.partition(".")
    target_files = [
        Path.home() / ".kage" / "config.toml",
        KAGE_DIR / "config.toml",
    ]

    success = False
    for tf in target_files:
        try:
            tf.parent.mkdir(parents=True, exist_ok=True)
            config = _load_toml_file(tf)

            if section not in config or not isinstance(config[section], dict):
                config[section] = {}

            if value.lower() == "true":
                typed_val = True
            elif value.lower() == "false":
                typed_val = False
            elif value.isdigit():
                typed_val = int(value)
            else:
                typed_val = value

            config[section][key] = typed_val

            _write_toml_file(tf, config)
            success = True
        except Exception as e:
            print(f"{C_RED}Failed writing to {tf}: {e}{C_RESET}")

    return success


def get_config_value(key_path: str) -> Optional[Any]:
    """Get config value by key path (e.g. llm.provider)."""
    cfg = _load_config()
    if "." in key_path:
        sec, _, k = key_path.partition(".")
        return cfg.get(sec, {}).get(k)
    return cfg.get(key_path)


def mask_secret(k: str, val: Any) -> str:
    """Mask API keys and sensitive tokens for safe logging/display."""
    sval = str(val)
    if any(secret_term in k.lower() for secret_term in ("key", "token", "secret", "password")):
        if len(sval) > 8:
            return sval[:4] + "***" + sval[-4:]
        return "***"
    return sval


# --- SLASH COMMAND HANDLERS ---

def handle_slash_models(line: str):
    """List available models for the active or all providers."""
    show_all = "--all" in line or "-a" in line
    cfg = _load_config()
    active_provider = cfg.get("llm", {}).get("provider", "gemini").lower()
    active_model = cfg.get("llm", {}).get("model", "")

    print(f"\n{C_BOLD}┌─── AVAILABLE LLM MODELS ───┐{C_RESET}")
    print(f"Active Provider: {C_CYAN}{active_provider}{C_RESET} | Active Model: {C_GREEN}{active_model}{C_RESET}\n")

    for p, models in PROVIDER_MODELS.items():
        if not show_all and p != active_provider:
            continue

        p_label = f"{C_BOLD}{p.upper()}{C_RESET}"
        if p == active_provider:
            p_label += f" {C_GREEN}[ACTIVE]{C_RESET}"
        print(p_label)

        if p == "ollama":
            try:
                out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
                if out.returncode == 0 and out.stdout.strip():
                    print(f"{C_DIM}{out.stdout.strip()}{C_RESET}")
                else:
                    for m in models:
                        prefix = "  • " if m != active_model else f"  {C_GREEN}* {C_RESET}"
                        print(f"{prefix}{m}")
            except Exception:
                for m in models:
                    prefix = "  • " if m != active_model else f"  {C_GREEN}* {C_RESET}"
                    print(f"{prefix}{m}")
        else:
            for m in models:
                prefix = "  • " if m != active_model else f"  {C_GREEN}* {C_RESET}"
                print(f"{prefix}{m}")
        print("")

    if not show_all:
        print(f"{C_DIM}Pass '/models --all' to see models across all supported providers.{C_RESET}")
    print(f"{C_BOLD}└────────────────────────────┘{C_RESET}")


def handle_slash_providers():
    """List configured providers and indicate active selection."""
    cfg = _load_config()
    active_provider = cfg.get("llm", {}).get("provider", "gemini").lower()

    print(f"\n{C_BOLD}┌─── CONFIGURED PROVIDERS ───┐{C_RESET}")
    for p in ["gemini", "groq", "openrouter", "ollama"]:
        status = f"{C_GREEN}[ACTIVE]{C_RESET}" if p == active_provider else f"{C_DIM}[STANDBY]{C_RESET}"
        models_count = len(PROVIDER_MODELS.get(p, []))
        print(f"  • {C_BOLD}{p:<12}{C_RESET} {status:<18} ({models_count} models)")
    print(f"{C_BOLD}└─────────────────────────────┘{C_RESET}")
    print(f"{C_DIM}Switch provider with: /config set llm.provider <provider_name>{C_RESET}")


def handle_slash_config(line: str):
    """Handle /config set <key> <value>, /config get <key>, or /config list."""
    parts = shlex.split(line)
    if len(parts) < 2 or parts[1] == "list":
        cfg = _load_config()
        print(f"\n{C_BOLD}┌─── CURRENT CONFIGURATION ───┐{C_RESET}")
        for sec, items in cfg.items():
            print(f"[{sec}]")
            if isinstance(items, dict):
                for k, v in items.items():
                    print(f"  {k} = \"{mask_secret(k, v)}\"")
            print("")
        print(f"{C_BOLD}└──────────────────────────────┘{C_RESET}")

    elif parts[1] == "get":
        if len(parts) < 3:
            print(f"{C_YELLOW}Usage: /config get <section.key> e.g. /config get llm.provider{C_RESET}")
            return
        key = parts[2]
        val = get_config_value(key)
        if val is not None:
            print(f"{C_GREEN}{key} = \"{mask_secret(key, val)}\"{C_RESET}")
        else:
            print(f"{C_YELLOW}Key '{key}' not found in configuration.{C_RESET}")

    elif parts[1] == "set":
        if len(parts) < 4:
            print(f"{C_YELLOW}Usage: /config set <section.key> <value> e.g. /config set llm.model llama-3.3-70b-versatile{C_RESET}")
            return
        key = parts[2]
        val = parts[3]
        if set_config_key(key, val):
            print(f"{C_GREEN}✓ Successfully set {key} = \"{val}\"{C_RESET}")
            if key == "llm.provider":
                print(f"{C_CYAN}ℹ Provider switched to '{val}'. Brain will reload dynamically on next call.{C_RESET}")
        else:
            print(f"{C_RED}❌ Failed to set configuration key.{C_RESET}")

    else:
        print(f"{C_YELLOW}Unknown config subcommand. Options: /config list, /config get <key>, /config set <key> <value>{C_RESET}")


# --- STANDALONE CLI SUBCOMMANDS ---

def cmd_logs(args):
    """TASK 1: Output or stream the daemon execution log using tail."""
    candidate_logs = [
        Path.home() / "kage-os" / "kage.log",
        Path.home() / ".kage" / "kage.log",
        KAGE_DIR / "kage.log",
    ]

    log_file = None
    for path in candidate_logs:
        if path.exists() and path.stat().st_size > 0:
            log_file = path
            break

    if not log_file:
        print(f"{C_YELLOW}⚠️ No logs found. Start the daemon with 'python3 kage.py' first.{C_RESET}")
        sys.exit(1)

    follow = getattr(args, "follow", False)
    cmd = ["tail", "-f" if follow else "-n", "50" if not follow else log_file, str(log_file)] if follow else ["tail", "-n", "50", str(log_file)]

    try:
        subprocess.run(cmd)
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"{C_RED}Error running tail: {e}{C_RESET}")
        sys.exit(1)


def cmd_schedule(args):
    """TASK 2: Query SQLite schedules table and format list."""
    sub = getattr(args, "subcmd", "list") or "list"

    if sub == "add":
        try:
            task_dict = json.loads(args.task) if isinstance(args.task, str) else args.task
        except json.JSONDecodeError as e:
            print(f"{C_RED}Invalid JSON task: {e}{C_RESET}")
            sys.exit(1)

        result = run_kage("schedule", {
            "subcmd": "add",
            "cron": args.cron,
            "agent": args.agent,
            "task_json": json.dumps(task_dict),
        })
        print(f"{C_GREEN if result.get('status') == 'done' else C_RED}{result.get('output', result)}{C_RESET}")
        sys.exit(0 if result.get("status") == "done" else 1)

    elif sub == "list":
        result = run_kage("schedule", {"subcmd": "list"})
        if result.get("status") == "done":
            jobs = result.get("output", [])
            if not jobs:
                print("📭 No scheduled jobs found. Add one with 'kage schedule add ...'")
                sys.exit(0)

            print(f"\n{C_BOLD}{'ID':<6} {'CRON EXPRESSION':<18} {'AGENT NAME':<15} {'TASK DATA':<35} {'ACTIVE'}{C_RESET}")
            print("─" * 85)
            for j in jobs:
                raw_task = j.get("task_json", "{}")
                task_str = raw_task if isinstance(raw_task, str) else json.dumps(raw_task)
                enabled = bool(j.get("enabled", 1))
                print(f"{j['id']:<6} {j['cron']:<18} {j['agent']:<15} {task_str[:35]:<35} {str(enabled)}")
            sys.exit(0)
        else:
            print(f"{C_RED}Error: {result.get('output')}{C_RESET}")
            sys.exit(1)

    elif sub == "delete":
        result = run_kage("schedule", {"subcmd": "delete", "job_id": args.job_id})
        print(f"{C_GREEN if result.get('status') == 'done' else C_RED}{result.get('output', result)}{C_RESET}")
        sys.exit(0 if result.get("status") == "done" else 1)


def cmd_test(args):
    """TASK 3: End-to-End WhatsApp bridge check and test message dispatcher."""
    target = getattr(args, "target", "whatsapp")
    if target != "whatsapp":
        print(f"{C_RED}Unknown test target: {target}{C_RESET}")
        sys.exit(1)

    print(f"{C_CYAN}[WHATSAPP TEST] Initiating end-to-end bridge health verification...{C_RESET}")

    cfg = _load_config()
    wa_config = cfg.get("whatsapp", {})
    test_number = wa_config.get("test_number", "1234567890")

    wake_res = run_kage("agent", {"subcmd": "wake", "agent": "whatsapp", "task": {"action": "status"}})

    if wake_res.get("status") != "done":
        print(f"{C_RED}❌ Bridge failed: Could not wake WhatsApp agent — {wake_res.get('output')}{C_RESET}")
        sys.exit(1)

    output = wake_res.get("output", {})
    conn_status = output.get("status", "disconnected") if isinstance(output, dict) else "unknown"

    print(f"[WHATSAPP TEST] Bridge Connection Status: {C_BOLD}{conn_status.upper()}{C_RESET}")

    if conn_status == "connected":
        if test_number and test_number != "1234567890":
            print(f"[WHATSAPP TEST] Sending verification ping to {test_number}...")
            send_res = run_kage("agent", {
                "subcmd": "wake",
                "agent": "whatsapp",
                "task": {"action": "send", "to": test_number, "text": "KAGE OS v2.1 WhatsApp Bridge Health Check OK ✅"}
            })

            if send_res.get("status") == "done":
                print(f"{C_GREEN}✅ WhatsApp bridge is alive and message delivered successfully!{C_RESET}")
                sys.exit(0)
            else:
                print(f"{C_RED}❌ Bridge failed: {send_res.get('output')}{C_RESET}")
                sys.exit(1)
        else:
            print(f"{C_GREEN}✅ WhatsApp bridge is alive! (Connection active; set 'test_number' in config.toml to test sending){C_RESET}")
            sys.exit(0)
    else:
        print(f"{C_RED}❌ Bridge failed: WhatsApp is currently {conn_status}. Scan QR code in terminal to pair device.{C_RESET}")
        sys.exit(1)


def cmd_chat(args):
    """Chat with Kage AI brain."""
    msg = args.message if hasattr(args, "message") else str(args)
    result = run_kage("chat", {"message": msg})

    if result.get("status") == "done":
        if "response" in result:
            print(f"\n> {result['response']}")
        if "brain_response" in result:
            print(f"\n> {result['brain_response']}")
        if "agent_result" in result:
            agent_result = result["agent_result"]
            if agent_result.get("status") == "done":
                output = agent_result.get("output", {})
                print(f"\n{C_BOLD}[EXECUTION OUTPUT]{C_RESET}")
                if isinstance(output, (dict, list)):
                    print(json.dumps(output, indent=2, default=str))
                else:
                    print(output)
            else:
                print(f"\n{C_RED}[EXECUTION ERROR]: {agent_result.get('output', 'unknown')}{C_RESET}")
        sys.exit(0)
    else:
        print(f"{C_RED}Error: {result.get('output', 'unknown')}{C_RESET}")
        sys.exit(1)


def cmd_status(args=None):
    """Show system overview status."""
    result = run_kage("status")
    if result.get("status") == "done":
        output = result.get("output", {})
        print(f"\n{C_BOLD}┌─── SYSTEM STATUS ───┐{C_RESET}")
        print(f"│ Agents Registered: {output.get('agents_registered', 0)}")
        print(f"│ Features Active:   Browser, OpenHands, MCP, CrewAI")
        print(f"│ Scheduled Jobs:    {output.get('scheduled_jobs', 0)}")
        print(f"│ Daemon Socket:     {C_GREEN if SOCKET_FILE.exists() else C_YELLOW}{'ONLINE' if SOCKET_FILE.exists() else 'STANDBY'}{C_RESET}")
        print(f"│ Workspace Dir:     {output.get('kage_dir', '?')}")
        print(f"{C_BOLD}└─────────────────────┘{C_RESET}")
        if args is None:  # In CLI mode
            sys.exit(0)
    else:
        print(f"{C_RED}Error: {result.get('output')}{C_RESET}")
        if args is None:
            sys.exit(1)


def cmd_health(args=None):
    """Check phone hardware telemetry."""
    result = run_kage("health")
    if result.get("status") == "done":
        output = result.get("output", {})
        print(f"\n{C_BOLD}┌─── SYSTEM TELEMETRY ───┐{C_RESET}")
        if "battery" in output:
            bat = output["battery"]
            if isinstance(bat, dict):
                if "percentage" in bat:
                    print(f"│ Battery:  {C_GREEN}{bat['percentage']}%{C_RESET} ({bat.get('status', 'unknown')})")
                elif "error" in bat:
                    print(f"│ Battery:  {bat['error']}")
        if "storage" in output:
            stor = output["storage"]
            if isinstance(stor, dict) and "total" in stor:
                print(f"│ Storage:  {stor['used']} / {stor['total']} ({stor.get('use_percent', '?')})")
            elif isinstance(stor, dict) and "error" in stor:
                print(f"│ Storage:  {stor['error']}")
        if "uptime" in output:
            print(f"│ Uptime:   {output['uptime']}")
        if "cpu" in output:
            cpu = output["cpu"]
            if isinstance(cpu, dict):
                if "raw" in cpu:
                    print(f"│ CPU Load: {cpu['raw'][:80]}")
                elif "load_average" in cpu:
                    print(f"│ CPU Load: {cpu['load_average']}")
        print(f"{C_BOLD}└────────────────────────┘{C_RESET}")
        if args is None:
            sys.exit(0)
    else:
        print(f"{C_RED}Error: {result.get('output')}{C_RESET}")
        if args is None:
            sys.exit(1)


def cmd_agent(args):
    """Manage domain personal agents."""
    sub = getattr(args, "subcmd", "list") or "list"

    if sub == "list":
        result = run_kage("agent", {"subcmd": "list"})
        if result.get("status") == "done":
            agents = result.get("output", [])
            print(f"\n{C_BOLD}{'AGENT':<15} {'STATUS':<10} {'DESCRIPTION'}{C_RESET}")
            print("─" * 70)
            for a in agents:
                status_color = C_GREEN if a['status'] == 'awake' else C_DIM
                print(f"{a['name']:<15} {status_color}{a['status']:<10}{C_RESET} {a.get('description', '')}")
            sys.exit(0)
        else:
            print(f"{C_RED}Error: {result.get('output')}{C_RESET}")
            sys.exit(1)

    elif sub == "wake":
        try:
            task_data = json.loads(args.task) if args.task else {}
        except json.JSONDecodeError as e:
            print(f"{C_RED}Invalid JSON in --task parameter: {e}{C_RESET}")
            sys.exit(1)

        result = run_kage("agent", {"subcmd": "wake", "agent": args.name, "task": task_data})
        if result.get("status") == "done":
            output = result.get("output", result)
            if isinstance(output, (dict, list)):
                print(json.dumps(output, indent=2, default=str))
            else:
                print(output)
            sys.exit(0)
        else:
            print(f"{C_RED}Error: {result.get('output')}{C_RESET}")
            sys.exit(1)

    elif sub == "create":
        result = run_kage("agent", {"subcmd": "create", "name": args.name})
        print(f"{C_GREEN if result.get('status') == 'done' else C_RED}{result.get('output', result)}{C_RESET}")
        sys.exit(0 if result.get("status") == "done" else 1)


def cmd_trace(args):
    """View trace execution history."""
    sub = getattr(args, "subcmd", "list") or "list"

    if sub == "list":
        limit = getattr(args, "limit", 20) or 20
        result = run_kage("trace", {"subcmd": "list", "limit": limit})
        if result.get("status") == "done":
            traces = result.get("output", [])
            if not traces:
                print("No traces recorded yet.")
                sys.exit(0)
            print(f"\n{C_BOLD}{'ID':<6} {'TIMESTAMP':<22} {'AGENT':<15} {'DURATION':<12} {'STATUS'}{C_RESET}")
            print("─" * 75)
            for t in traces:
                err = f"{C_GREEN}OK{C_RESET}" if not t.get("error") else f"{C_RED}FAIL{C_RESET}"
                dur_val = t.get("duration_ms")
                dur = f"{dur_val:.0f}ms" if dur_val is not None else "?"
                ts = t.get("timestamp", "")[:19]
                print(f"{t['id']:<6} {ts:<22} {t['agent']:<15} {dur:<12} {err}")
            sys.exit(0)
        else:
            print(f"{C_RED}Error: {result.get('output')}{C_RESET}")
            sys.exit(1)

    elif sub == "show":
        result = run_kage("trace", {"subcmd": "show", "trace_id": args.trace_id})
        if result.get("status") == "done":
            t = result.get("output")
            if t:
                print(json.dumps(t, indent=2, default=str))
                sys.exit(0)
            else:
                print(f"{C_YELLOW}Trace {args.trace_id} not found{C_RESET}")
                sys.exit(1)
        else:
            print(f"{C_RED}Error: {result.get('output')}{C_RESET}")
            sys.exit(1)


def cmd_daemon(args):
    """Manage background supervisor daemon process."""
    sub = getattr(args, "action", "status") or "status"

    if sub == "start":
        if SOCKET_FILE.exists():
            print(f"{C_GREEN}[DAEMON] Already running.{C_RESET}")
            sys.exit(0)

        print("[DAEMON] Starting background supervisor daemon...")
        subprocess.Popen(
            [PYTHON, str(KAGE_DIR / "kage.py"), "daemon"],
            cwd=str(KAGE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(1)
        if SOCKET_FILE.exists():
            print(f"{C_GREEN}[DAEMON] Started successfully.{C_RESET}")
            sys.exit(0)
        else:
            print(f"{C_YELLOW}[DAEMON] Starting... Use 'kage status' to verify.{C_RESET}")
            sys.exit(0)

    elif sub == "stop":
        result = run_kage("stop")
        print(f"{C_GREEN}{result.get('output', 'Stop command sent.')}{C_RESET}")
        sys.exit(0)

    elif sub == "status":
        if SOCKET_FILE.exists():
            print(f"{C_GREEN}[DAEMON] Active socket at {SOCKET_FILE}{C_RESET}")
            cmd_status(args)
        else:
            print(f"{C_YELLOW}[DAEMON] Not running. Use 'kage daemon start' to activate service.{C_RESET}")
            sys.exit(1)


# --- INTERACTIVE REPL SHELL ---

def start_interactive_repl():
    """Start continuous interactive Terminal REPL shell for Termux (OpenCode Style)."""
    print(ASCII_BANNER)
    print("")

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if HISTORY_FILE.exists():
        try:
            readline.read_history_file(str(HISTORY_FILE))
        except Exception:
            pass

    readline.set_history_length(1000)

    def save_history():
        try:
            readline.write_history_file(str(HISTORY_FILE))
        except Exception:
            pass

    import atexit
    atexit.register(save_history)

    while True:
        try:
            line = input(f"{C_BOLD}KAGE>{C_RESET} ").strip()
            if not line:
                continue

            if line in ("/exit", "/quit", "exit", "quit"):
                print(f"\n{C_CYAN}[KAGE OS] Exiting interactive session. Goodbye.{C_RESET}")
                break

            elif line.startswith("/help"):
                print(f"""
{C_BOLD}┌─── KAGE OS SLASH COMMANDS ───┐{C_RESET}
│  {C_CYAN}/models{C_RESET}             - List available models for active provider (/models --all)
│  {C_CYAN}/providers{C_RESET}          - List configured LLM providers & active selection
│  {C_CYAN}/config list{C_RESET}        - Display full configuration (secrets masked)
│  {C_CYAN}/config get <key>{C_RESET}   - Show specific config value e.g. /config get llm.model
│  {C_CYAN}/config set <key> <val>{C_RESET} - Update config value e.g. /config set llm.provider groq
│  {C_CYAN}/status{C_RESET}             - System status & IPC socket
│  {C_CYAN}/health{C_RESET}             - Check battery, storage, CPU, uptime
│  {C_CYAN}/agents{C_RESET}             - List registered personal domain agents
│  {C_CYAN}/traces{C_RESET}             - List recent trace execution logs
│  {C_CYAN}/schedules{C_RESET}          - List active cron schedules
│  {C_CYAN}/clear{C_RESET}              - Clear terminal screen
│  {C_CYAN}/exit{C_RESET}               - Exit interactive session
│  {C_GREEN}<prompt>{C_RESET}            - Chat directly with Kage LLM Brain
{C_BOLD}└────────────────────────────────────┘{C_RESET}""")

            elif line.startswith("/models"):
                handle_slash_models(line)

            elif line.startswith("/providers"):
                handle_slash_providers()

            elif line.startswith("/config"):
                handle_slash_config(line)

            elif line == "/status":
                cmd_status("repl")

            elif line == "/health":
                cmd_health("repl")

            elif line == "/agents":
                res = run_kage("agent", {"subcmd": "list"})
                if res.get("status") == "done":
                    agents = res.get("output", [])
                    print(f"\n{C_BOLD}{'AGENT':<15} {'STATUS':<10} {'DESCRIPTION'}{C_RESET}")
                    print("─" * 70)
                    for a in agents:
                        st_col = C_GREEN if a['status'] == 'awake' else C_DIM
                        print(f"{a['name']:<15} {st_col}{a['status']:<10}{C_RESET} {a.get('description', '')}")

            elif line == "/traces":
                res = run_kage("trace", {"subcmd": "list", "limit": 10})
                if res.get("status") == "done":
                    traces = res.get("output", [])
                    print(f"\n{C_BOLD}{'ID':<6} {'TIMESTAMP':<22} {'AGENT':<15} {'DURATION':<12} {'STATUS'}{C_RESET}")
                    print("─" * 75)
                    for t in traces:
                        err = f"{C_GREEN}OK{C_RESET}" if not t.get("error") else f"{C_RED}FAIL{C_RESET}"
                        dur_val = t.get("duration_ms")
                        dur = f"{dur_val:.0f}ms" if dur_val is not None else "?"
                        ts = t.get("timestamp", "")[:19]
                        print(f"{t['id']:<6} {ts:<22} {t['agent']:<15} {dur:<12} {err}")

            elif line == "/schedules":
                res = run_kage("schedule", {"subcmd": "list"})
                if res.get("status") == "done":
                    jobs = res.get("output", [])
                    if not jobs:
                        print("📭 No scheduled jobs found.")
                    else:
                        print(f"\n{C_BOLD}{'ID':<6} {'CRON':<18} {'AGENT':<15} {'TASK'}{C_RESET}")
                        print("─" * 65)
                        for j in jobs:
                            print(f"{j['id']:<6} {j['cron']:<18} {j['agent']:<15} {str(j.get('task_json', ''))[:35]}")

            elif line == "/clear":
                os.system("clear" if os.name != "nt" else "cls")
                print(ASCII_BANNER)

            else:
                res = run_kage("chat", {"message": line})
                if res.get("status") == "done":
                    if "response" in res:
                        print(f"\n{C_GREEN}> {res['response']}{C_RESET}")
                    if "brain_response" in res:
                        print(f"\n{C_GREEN}> {res['brain_response']}{C_RESET}")
                    if "agent_result" in res and res["agent_result"]:
                        ag = res["agent_result"]
                        output = ag.get("output", {})
                        print(f"\n{C_BOLD}[EXECUTION OUTPUT]{C_RESET}")
                        if isinstance(output, (dict, list)):
                            print(json.dumps(output, indent=2, default=str))
                        else:
                            print(output)
                else:
                    print(f"\n{C_RED}Error: {res.get('output')}{C_RESET}")

        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{C_CYAN}[KAGE OS] Exiting interactive shell. Goodbye.{C_RESET}")
            break


def main():
    parser = argparse.ArgumentParser(
        prog="kage",
        description="KAGE OS — Terminal AI Operating System for Termux",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("interactive", help="Start OpenCode-style interactive terminal shell")

    p_chat = subparsers.add_parser("chat", help="Chat with Kage LLM brain")
    p_chat.add_argument("message", help="Message or instruction")

    p_logs = subparsers.add_parser("logs", help="View daemon log file tail")
    p_logs.add_argument("-f", "--follow", action="store_true", help="Stream daemon log in real-time")

    p_sched = subparsers.add_parser("schedule", help="Cron job schedule management")
    sched_sub = p_sched.add_subparsers(dest="subcmd")
    sched_sub.add_parser("list", help="List scheduled jobs in database")
    p_sa = sched_sub.add_parser("add", help="Add new scheduled task")
    p_sa.add_argument("--cron", required=True, help="Cron syntax e.g. '0 9 * * *'")
    p_sa.add_argument("--agent", required=True, help="Target agent name")
    p_sa.add_argument("--task", required=True, help="JSON task object")
    p_sd = sched_sub.add_parser("delete", help="Delete scheduled job by ID")
    p_sd.add_argument("job_id", type=int, help="Job ID")

    p_test = subparsers.add_parser("test", help="Run system & agent integration tests")
    p_test.add_argument("target", choices=["whatsapp"], help="Integration test target (e.g. whatsapp)")

    p_agent = subparsers.add_parser("agent", help="Agent management")
    agent_sub = p_agent.add_subparsers(dest="subcmd")
    agent_sub.add_parser("list", help="List all registered domain agents")
    p_aw = agent_sub.add_parser("wake", help="Wake an agent with task")
    p_aw.add_argument("name", help="Agent name")
    p_aw.add_argument("--task", default="{}", help="JSON task object")
    p_ac = agent_sub.add_parser("create", help="Create new custom agent scaffold")
    p_ac.add_argument("name", help="Agent name")

    p_trace = subparsers.add_parser("trace", help="Trace execution history")
    trace_sub = p_trace.add_subparsers(dest="subcmd")
    p_tl = trace_sub.add_parser("list", help="List recent execution traces")
    p_tl.add_argument("--limit", type=int, default=20, help="Max traces")
    p_ts = trace_sub.add_parser("show", help="Show details for trace ID")
    p_ts.add_argument("trace_id", type=int, help="Trace ID")

    subparsers.add_parser("health", help="Check phone health (battery, storage, CPU)")
    subparsers.add_parser("status", help="Show system overview status")

    p_daemon = subparsers.add_parser("daemon", help="Manage background daemon service")
    p_daemon.add_argument("action", choices=["start", "stop", "status"], nargs="?", default="status", help="Action")

    args = parser.parse_args()

    if not args.command or args.command == "interactive":
        start_interactive_repl()
        return

    dispatch = {
        "chat": cmd_chat,
        "logs": cmd_logs,
        "schedule": cmd_schedule,
        "test": cmd_test,
        "agent": cmd_agent,
        "trace": cmd_trace,
        "health": cmd_health,
        "status": cmd_status,
        "daemon": cmd_daemon,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()
