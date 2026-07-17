#!/usr/bin/env python3
"""
kage_cli.py — User-facing CLI. All commands listed in the spec.

Usage:
  kage chat "message"
  kage agent list
  kage agent wake <name> --task '{"key":"val"}'
  kage agent create <name>
  kage trace list
  kage trace show <id>
  kage health
  kage schedule add --cron "0 9 * * *" --agent obsidian --task '{"action":"daily_summary"}'
  kage schedule list
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

KAGE_DIR = Path(__file__).parent
PYTHON = sys.executable


def run_kage(command: str, args: dict = None) -> dict:
    """Run a command through the KAGE daemon."""
    cmd_json = json.dumps({"command": command, "args": args or {}})

    # Try running kage.py with the command
    try:
        result = subprocess.run(
            [PYTHON, str(KAGE_DIR / "kage.py"), command, json.dumps(args or {})],
            capture_output=True, text=True, timeout=60,
            cwd=str(KAGE_DIR),
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        else:
            return {"status": "error", "output": result.stderr or "No output"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "output": "Command timed out"}
    except json.JSONDecodeError:
        return {"status": "error", "output": result.stdout or result.stderr}
    except Exception as e:
        return {"status": "error", "output": str(e)}


def cmd_chat(args):
    """Chat with Kage."""
    result = run_kage("chat", {"message": args.message})

    if result.get("status") == "done":
        if "response" in result:
            print(f"\nKage: {result['response']}")
        if "brain_response" in result:
            print(f"\nKage: {result['brain_response']}")
        if "agent_result" in result:
            agent_result = result["agent_result"]
            if agent_result.get("status") == "done":
                output = agent_result.get("output", {})
                print(f"\nAgent Result:")
                print(json.dumps(output, indent=2, default=str))
            else:
                print(f"\nAgent Error: {agent_result.get('output', 'unknown')}")
    else:
        print(f"Error: {result.get('output', 'unknown')}")


def cmd_agent(args):
    """Agent management."""
    if args.subcmd == "list":
        result = run_kage("agent", {"subcmd": "list"})
        if result.get("status") == "done":
            agents = result.get("output", [])
            print(f"\n{'Name':<15} {'Status':<10} {'Description'}")
            print("─" * 60)
            for a in agents:
                print(f"{a['name']:<15} {a['status']:<10} {a.get('description', '')}")
        else:
            print(f"Error: {result.get('output')}")

    elif args.subcmd == "wake":
        task_data = json.loads(args.task) if args.task else {}
        result = run_kage("agent", {"subcmd": "wake", "agent": args.name, "task": task_data})
        if result.get("status") == "done":
            output = result.get("output", result)
            if isinstance(output, dict):
                print(json.dumps(output, indent=2, default=str))
            else:
                print(output)
        else:
            print(f"Error: {result.get('output')}")

    elif args.subcmd == "create":
        result = run_kage("agent", {"subcmd": "create", "name": args.name})
        print(result.get("output", result))


def cmd_trace(args):
    """Trace management."""
    if args.subcmd == "list":
        result = run_kage("trace", {"subcmd": "list", "limit": args.limit})
        if result.get("status") == "done":
            traces = result.get("output", [])
            if not traces:
                print("No traces yet.")
                return
            print(f"\n{'ID':<6} {'Timestamp':<22} {'Agent':<15} {'Duration':<12} {'Error'}")
            print("─" * 75)
            for t in traces:
                err = "✓" if not t.get("error") else "✗"
                dur = f"{t['duration_ms']:.0f}ms" if t.get("duration_ms") else "?"
                print(f"{t['id']:<6} {t['timestamp']:<22} {t['agent']:<15} {dur:<12} {err}")
        else:
            print(f"Error: {result.get('output')}")

    elif args.subcmd == "show":
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
        print("\n═══ KAGE HEALTH ═══")
        if "battery" in output:
            bat = output["battery"]
            if "percentage" in bat:
                print(f"  Battery: {bat['percentage']}% ({bat.get('status', 'unknown')})")
            elif "error" in bat:
                print(f"  Battery: {bat['error']}")
        if "storage" in output:
            stor = output["storage"]
            if "total" in stor:
                print(f"  Storage: {stor['used']}/{stor['total']} ({stor.get('use_percent', '?')})")
        if "uptime" in output:
            print(f"  Uptime: {output['uptime']}")
        if "cpu" in output:
            cpu = output["cpu"]
            if "raw" in cpu:
                print(f"  CPU: {cpu['raw'][:100]}")
        print("═════════════════════")
    else:
        print(f"Error: {result.get('output')}")


def cmd_schedule(args):
    """Schedule management."""
    if args.subcmd == "add":
        result = run_kage("schedule", {
            "subcmd": "add",
            "cron": args.cron,
            "agent": args.agent,
            "task_json": args.task,
        })
        print(result.get("output", result))

    elif args.subcmd == "list":
        result = run_kage("schedule", {"subcmd": "list"})
        if result.get("status") == "done":
            jobs = result.get("output", [])
            if not jobs:
                print("No scheduled jobs.")
                return
            print(f"\n{'ID':<6} {'Cron':<18} {'Agent':<15} {'Task'}")
            print("─" * 65)
            for j in jobs:
                task = json.loads(j["task_json"]) if isinstance(j["task_json"], str) else j["task_json"]
                print(f"{j['id']:<6} {j['cron']:<18} {j['agent']:<15} {json.dumps(task)[:40]}")
        else:
            print(f"Error: {result.get('output')}")

    elif args.subcmd == "delete":
        result = run_kage("schedule", {"subcmd": "delete", "job_id": args.job_id})
        print(result.get("output", result))


def cmd_status(args):
    """System status."""
    result = run_kage("status")
    if result.get("status") == "done":
        output = result.get("output", {})
        print("\n═══ KAGE STATUS ═══")
        print(f"  Agents registered: {output.get('agents_registered', 0)}")
        print(f"  Agents loaded:     {output.get('agents_loaded', 0)}")
        print(f"  Agents awake:      {output.get('agents_awake', 0)}")
        print(f"  Kage dir:          {output.get('kage_dir', '?')}")
        print("═══════════════════")
    else:
        print(f"Error: {result.get('output')}")


def main():
    parser = argparse.ArgumentParser(
        prog="kage",
        description="KAGE OS — Personal AI Agent System",
    )
    subparsers = parser.add_subparsers(dest="command")

    # chat
    p_chat = subparsers.add_parser("chat", help="Chat with Kage")
    p_chat.add_argument("message", help="Message to send")

    # agent
    p_agent = subparsers.add_parser("agent", help="Agent management")
    agent_sub = p_agent.add_subparsers(dest="subcmd")
    agent_sub.add_parser("list", help="List agents")
    p_aw = agent_sub.add_parser("wake", help="Wake an agent")
    p_aw.add_argument("name", help="Agent name")
    p_aw.add_argument("--task", default="{}", help="JSON task data")
    p_ac = agent_sub.add_parser("create", help="Create new agent")
    p_ac.add_argument("name", help="Agent name")

    # trace
    p_trace = subparsers.add_parser("trace", help="Trace management")
    trace_sub = p_trace.add_subparsers(dest="subcmd")
    p_tl = trace_sub.add_parser("list", help="List traces")
    p_tl.add_argument("--limit", type=int, default=20, help="Max traces")
    p_ts = trace_sub.add_parser("show", help="Show trace")
    p_ts.add_argument("trace_id", type=int, help="Trace ID")

    # health
    subparsers.add_parser("health", help="Check phone health")

    # schedule
    p_sched = subparsers.add_parser("schedule", help="Schedule management")
    sched_sub = p_sched.add_subparsers(dest="subcmd")
    p_sa = sched_sub.add_parser("add", help="Add schedule")
    p_sa.add_argument("--cron", required=True, help="Cron expression")
    p_sa.add_argument("--agent", required=True, help="Agent name")
    p_sa.add_argument("--task", required=True, help="JSON task data")
    sched_sub.add_parser("list", help="List schedules")
    p_sd = sched_sub.add_parser("delete", help="Delete schedule")
    p_sd.add_argument("job_id", type=int, help="Job ID")

    # status
    subparsers.add_parser("status", help="System status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    dispatch = {
        "chat": cmd_chat,
        "agent": cmd_agent,
        "trace": cmd_trace,
        "health": cmd_health,
        "schedule": cmd_schedule,
        "status": cmd_status,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()