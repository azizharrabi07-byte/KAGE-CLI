#!/usr/bin/env python3
"""
kage_cli.py — Minimalist Black & White OpenCode-Style CLI for KAGE OS.

Usage:
  kage chat "message"
  kage web [--port 8080]
  kage agent list
  kage agent wake <name> --task '{"key":"val"}'
  kage agent create <name>
  kage trace list
  kage trace show <id>
  kage health
  kage schedule add --cron "0 9 * * *" --agent system --task '{"action":"health"}'
  kage schedule list
  kage schedule delete <job_id>
  kage daemon start|stop|status
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

KAGE_DIR = Path(__file__).parent
PYTHON = sys.executable
SOCKET_FILE = Path.home() / ".kage" / "kage.sock"


def run_kage(command: str, args: dict = None) -> dict:
    """Run a command through the KAGE daemon socket or direct execution fallback."""
    args = args or {}
    cmd_payload = json.dumps({"command": command, "args": args})

    # 1. Try sending via Unix socket to running daemon
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

    # 2. Direct execution fallback
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


def cmd_chat(args):
    """Chat with Kage."""
    result = run_kage("chat", {"message": args.message})

    if result.get("status") == "done":
        if "response" in result:
            print(f"\n> {result['response']}")
        if "brain_response" in result:
            print(f"\n> {result['brain_response']}")
        if "agent_result" in result:
            agent_result = result["agent_result"]
            if agent_result.get("status") == "done":
                output = agent_result.get("output", {})
                print(f"\n[AGENT OUTPUT]")
                if isinstance(output, (dict, list)):
                    print(json.dumps(output, indent=2, default=str))
                else:
                    print(output)
            else:
                print(f"\n[AGENT ERROR]: {agent_result.get('output', 'unknown')}")
    else:
        print(f"Error: {result.get('output', 'unknown')}")


def cmd_web(args):
    """Start KAGE OS OpenCode-Style Web Landing Page & Dashboard."""
    port = getattr(args, "port", 8080)
    print(f"[OPENCODE DASHBOARD] Running on http://localhost:{port}")
    subprocess.run([PYTHON, str(KAGE_DIR / "core" / "web_ui.py"), str(port)], cwd=str(KAGE_DIR))


def cmd_agent(args):
    """Agent management."""
    sub = getattr(args, "subcmd", "list") or "list"

    if sub == "list":
        result = run_kage("agent", {"subcmd": "list"})
        if result.get("status") == "done":
            agents = result.get("output", [])
            print(f"\n{'AGENT':<15} {'STATUS':<10} {'DESCRIPTION'}")
            print("─" * 70)
            for a in agents:
                print(f"{a['name']:<15} {a['status']:<10} {a.get('description', '')}")
        else:
            print(f"Error: {result.get('output')}")

    elif sub == "wake":
        try:
            task_data = json.loads(args.task) if args.task else {}
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in --task parameter: {e}")
            return

        result = run_kage("agent", {"subcmd": "wake", "agent": args.name, "task": task_data})
        if result.get("status") == "done":
            output = result.get("output", result)
            if isinstance(output, (dict, list)):
                print(json.dumps(output, indent=2, default=str))
            else:
                print(output)
        else:
            print(f"Error: {result.get('output')}")

    elif sub == "create":
        result = run_kage("agent", {"subcmd": "create", "name": args.name})
        print(result.get("output", result))


def cmd_trace(args):
    """Trace management."""
    sub = getattr(args, "subcmd", "list") or "list"

    if sub == "list":
        result = run_kage("trace", {"subcmd": "list", "limit": args.limit})
        if result.get("status") == "done":
            traces = result.get("output", [])
            if not traces:
                print("No traces recorded yet.")
                return
            print(f"\n{'ID':<6} {'TIMESTAMP':<22} {'AGENT':<15} {'DURATION':<12} {'STATUS'}")
            print("─" * 75)
            for t in traces:
                err = "OK" if not t.get("error") else "FAIL"
                dur_val = t.get("duration_ms")
                dur = f"{dur_val:.0f}ms" if dur_val is not None else "?"
                ts = t.get("timestamp", "")[:19]
                print(f"{t['id']:<6} {ts:<22} {t['agent']:<15} {dur:<12} {err}")
        else:
            print(f"Error: {result.get('output')}")

    elif sub == "show":
        result = run_kage("trace", {"subcmd": "show", "trace_id": args.trace_id})
        if result.get("status") == "done":
            t = result.get("output")
            if t:
                print(json.dumps(t, indent=2, default=str))
            else:
                print(f"Trace {args.trace_id} not found")
        else:
            print(f"Error: {result.get('output')}")


def cmd_health(args):
    """Check phone health."""
    result = run_kage("health")
    if result.get("status") == "done":
        output = result.get("output", {})
        print("\n┌─── SYSTEM TELEMETRY ───┐")
        if "battery" in output:
            bat = output["battery"]
            if isinstance(bat, dict):
                if "percentage" in bat:
                    print(f"│ Battery:  {bat['percentage']}% ({bat.get('status', 'unknown')})")
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
        print("└────────────────────────┘")
    else:
        print(f"Error: {result.get('output')}")


def cmd_schedule(args):
    """Schedule management."""
    sub = getattr(args, "subcmd", "list") or "list"

    if sub == "add":
        try:
            task_dict = json.loads(args.task) if isinstance(args.task, str) else args.task
        except json.JSONDecodeError as e:
            print(f"Invalid JSON task: {e}")
            return

        result = run_kage("schedule", {
            "subcmd": "add",
            "cron": args.cron,
            "agent": args.agent,
            "task_json": json.dumps(task_dict),
        })
        print(result.get("output", result))

    elif sub == "list":
        result = run_kage("schedule", {"subcmd": "list"})
        if result.get("status") == "done":
            jobs = result.get("output", [])
            if not jobs:
                print("No scheduled jobs.")
                return
            print(f"\n{'ID':<6} {'CRON':<18} {'AGENT':<15} {'TASK'}")
            print("─" * 65)
            for j in jobs:
                raw_task = j.get("task_json", "{}")
                task_str = raw_task if isinstance(raw_task, str) else json.dumps(raw_task)
                print(f"{j['id']:<6} {j['cron']:<18} {j['agent']:<15} {task_str[:35]}")
        else:
            print(f"Error: {result.get('output')}")

    elif sub == "delete":
        result = run_kage("schedule", {"subcmd": "delete", "job_id": args.job_id})
        print(result.get("output", result))


def cmd_status(args):
    """System status."""
    result = run_kage("status")
    if result.get("status") == "done":
        output = result.get("output", {})
        print("\n┌─── SYSTEM STATUS ───┐")
        print(f"│ Agents Registered: {output.get('agents_registered', 0)}")
        print(f"│ Agents Loaded:     {output.get('agents_loaded', 0)}")
        print(f"│ Agents Awake:      {output.get('agents_awake', 0)}")
        print(f"│ Scheduled Jobs:    {output.get('scheduled_jobs', 0)}")
        print(f"│ Daemon Socket:     {'ONLINE' if SOCKET_FILE.exists() else 'OFFLINE'}")
        print(f"│ Directory:         {output.get('kage_dir', '?')}")
        print("└─────────────────────┘")
    else:
        print(f"Error: {result.get('output')}")


def cmd_daemon(args):
    """Manage supervisor daemon process."""
    sub = getattr(args, "action", "status") or "status"

    if sub == "start":
        if SOCKET_FILE.exists():
            print("[DAEMON] Already running.")
            return

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
            print("[DAEMON] Started successfully.")
        else:
            print("[DAEMON] Starting... Use 'kage status' to verify.")

    elif sub == "stop":
        result = run_kage("stop")
        print(result.get("output", "Stop command sent."))

    elif sub == "status":
        if SOCKET_FILE.exists():
            print("[DAEMON] Active socket at", SOCKET_FILE)
            cmd_status(args)
        else:
            print("[DAEMON] Not running. Use 'kage daemon start' to activate service.")


def main():
    parser = argparse.ArgumentParser(
        prog="kage",
        description="KAGE OS — OpenCode-Style Personal AI Operating System",
    )
    subparsers = parser.add_subparsers(dest="command")

    # chat
    p_chat = subparsers.add_parser("chat", help="Chat with Kage LLM brain")
    p_chat.add_argument("message", help="Message or instruction")

    # web
    p_web = subparsers.add_parser("web", help="Start OpenCode-style Web Dashboard")
    p_web.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")

    # agent
    p_agent = subparsers.add_parser("agent", help="Agent management")
    agent_sub = p_agent.add_subparsers(dest="subcmd")
    agent_sub.add_parser("list", help="List all registered agents")
    p_aw = agent_sub.add_parser("wake", help="Wake an agent with task")
    p_aw.add_argument("name", help="Agent name")
    p_aw.add_argument("--task", default="{}", help="JSON task object")
    p_ac = agent_sub.add_parser("create", help="Create new custom agent scaffold")
    p_ac.add_argument("name", help="Agent name")

    # trace
    p_trace = subparsers.add_parser("trace", help="Trace execution history")
    trace_sub = p_trace.add_subparsers(dest="subcmd")
    p_tl = trace_sub.add_parser("list", help="List recent execution traces")
    p_tl.add_argument("--limit", type=int, default=20, help="Max traces")
    p_ts = trace_sub.add_parser("show", help="Show details for trace ID")
    p_ts.add_argument("trace_id", type=int, help="Trace ID")

    # health
    subparsers.add_parser("health", help="Check phone health (battery, storage, CPU)")

    # schedule
    p_sched = subparsers.add_parser("schedule", help="Cron job schedule management")
    sched_sub = p_sched.add_subparsers(dest="subcmd")
    p_sa = sched_sub.add_parser("add", help="Add new scheduled task")
    p_sa.add_argument("--cron", required=True, help="Cron syntax e.g. '0 9 * * *'")
    p_sa.add_argument("--agent", required=True, help="Target agent name")
    p_sa.add_argument("--task", required=True, help="JSON task object")
    sched_sub.add_parser("list", help="List active schedules")
    p_sd = sched_sub.add_parser("delete", help="Delete scheduled job by ID")
    p_sd.add_argument("job_id", type=int, help="Job ID")

    # status
    subparsers.add_parser("status", help="Show system overview status")

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Manage background daemon service")
    p_daemon.add_argument("action", choices=["start", "stop", "status"], nargs="?", default="status", help="Action")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    dispatch = {
        "chat": cmd_chat,
        "web": cmd_web,
        "agent": cmd_agent,
        "trace": cmd_trace,
        "health": cmd_health,
        "schedule": cmd_schedule,
        "status": cmd_status,
        "daemon": cmd_daemon,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()
