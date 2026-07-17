#!/usr/bin/env python3
"""
kage.py — Main daemon / supervisor loop.
Runs as background process, listens for CLI commands via lock file + stdin.
"""

import json
import os
import sys
import time
import signal
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

KAGE_DIR = Path(__file__).parent
LOCK_FILE = KAGE_DIR / ".kage.lock"
LOG_FILE = KAGE_DIR / "kage.log"


class Kage:
    """The supervisor brain. Wakes agents, manages state."""

    def __init__(self):
        self.running = True
        self.agents_dir = KAGE_DIR / "agents"
        self.context = None  # Set after init
        self._loaded_agents = {}  # Cache of loaded agent modules

    def log(self, msg: str, level: str = "INFO"):
        """Log to file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] {msg}"
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")

    def init_context(self):
        """Initialize the shared context (brain, memory, permissions)."""
        from core import memory, permissions

        self.context = type("Context", (), {
            "brain": self,
            "memory": memory,
            "permissions": permissions,
        })()
        memory.init_db()
        self.log("Context initialized")

    def load_agent(self, agent_name: str):
        """Load an agent module (lazy import)."""
        if agent_name in self._loaded_agents:
            return self._loaded_agents[agent_name]

        registry_path = self.agents_dir / "registry.json"
        if not registry_path.exists():
            self.log(f"Registry not found", "ERROR")
            return None

        with open(registry_path) as f:
            registry = json.load(f)

        if agent_name not in registry:
            self.log(f"Agent '{agent_name}' not in registry", "ERROR")
            return None

        agent_info = registry[agent_name]
        agent_path = self.agents_dir / agent_info["path"]
        agent_py = agent_path / "agent.py"

        if not agent_py.exists():
            self.log(f"Agent file not found: {agent_py}", "ERROR")
            return None

        # Dynamic import
        spec = importlib.util.spec_from_file_location(
            f"agents.{agent_name}", str(agent_py)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        agent_instance = module.Agent(self.context)
        self._loaded_agents[agent_name] = agent_instance
        return agent_instance

    def wake(self, agent_name: str, task_data: dict) -> dict:
        """Wake an agent, execute task, then sleep it."""
        self.log(f"Waking agent: {agent_name}")

        agent = self.load_agent(agent_name)
        if not agent:
            return {"status": "error", "output": f"Agent '{agent_name}' not found"}

        start_time = time.time()
        try:
            result = agent.wake(task_data)
        except Exception as e:
            result = {"status": "error", "output": str(e)}
            self.log(f"Agent {agent_name} error: {e}", "ERROR")
        finally:
            duration_ms = (time.time() - start_time) * 1000

            # Log trace
            try:
                from core.memory import log_trace
                log_trace(
                    agent=agent_name,
                    task=task_data,
                    output=result if result.get("status") == "done" else None,
                    error=result.get("output") if result.get("status") == "error" else None,
                    duration_ms=duration_ms,
                )
            except Exception:
                pass

            self.log(f"Agent {agent_name} done in {duration_ms:.0f}ms")

        return result

    def process_command(self, command: str, args: dict) -> dict:
        """Process a CLI command and return the result."""
        if command == "chat":
            return self._handle_chat(args.get("message", ""))
        elif command == "agent":
            return self._handle_agent_command(args)
        elif command == "trace":
            return self._handle_trace(args)
        elif command == "health":
            return self.wake("system", {})
        elif command == "schedule":
            return self._handle_schedule(args)
        elif command == "status":
            return self._handle_status()
        else:
            return {"status": "error", "output": f"Unknown command: {command}"}

    def _handle_chat(self, message: str) -> dict:
        """Route a chat message through the brain."""
        from core.brain import call_llm, KAGE_SYSTEM_PROMPT

        result = call_llm(
            messages=[{"role": "user", "content": message}],
            system=KAGE_SYSTEM_PROMPT,
        )

        content = result.get("content", "")

        # Check if the brain wants to call an agent
        try:
            # Look for JSON action block in the response
            if '{"action"' in content:
                import re
                match = re.search(r'\{[^{}]*"action"[^{}]*\}', content)
                if match:
                    action = json.loads(match.group())
                    agent_name = action.get("action", "")
                    task_data = action.get("task", {})
                    if agent_name and task_data:
                        agent_result = self.wake(agent_name, task_data)
                        return {
                            "status": "done",
                            "input": message,
                            "brain_response": content,
                            "agent_result": agent_result,
                        }
        except (json.JSONDecodeError, Exception):
            pass

        return {"status": "done", "input": message, "response": content}

    def _handle_agent_command(self, args: dict) -> dict:
        """Handle agent subcommands."""
        sub = args.get("subcmd", "list")

        if sub == "list":
            registry_path = self.agents_dir / "registry.json"
            if registry_path.exists():
                with open(registry_path) as f:
                    registry = json.load(f)
            else:
                registry = {}

            result = []
            for name, info in registry.items():
                agent = self._loaded_agents.get(name)
                status = "awake" if agent and agent.alive else "sleeping"
                result.append({"name": name, "status": status, "description": info.get("description", "")})
            return {"status": "done", "output": result}

        elif sub == "wake":
            agent_name = args.get("agent", "")
            task_data = args.get("task", {})
            return self.wake(agent_name, task_data)

        elif sub == "create":
            agent_name = args.get("name", "")
            return self._create_agent(agent_name)

        return {"status": "error", "output": f"Unknown agent subcommand: {sub}"}

    def _create_agent(self, name: str) -> dict:
        """Scaffold a new agent."""
        agent_dir = self.agents_dir / name
        agent_dir.mkdir(parents=True, exist_ok=True)

        agent_py = agent_dir / "agent.py"
        agent_py.write_text(f'''#!/usr/bin/env python3
"""Agent: {name}"""

import gc
import sys
from typing import Dict


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False

    def wake(self, task_data: dict) -> dict:
        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        # Implement your logic here
        return {{"status": "done", "output": "Not implemented yet"}}

    def sleep(self):
        self.alive = False
        gc.collect()
''')

        # Add to registry
        registry_path = self.agents_dir / "registry.json"
        if registry_path.exists():
            with open(registry_path) as f:
                registry = json.load(f)
        else:
            registry = {}

        registry[name] = {
            "path": name,
            "timeout": 30,
            "description": f"Custom agent: {name}",
        }

        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=4)

        return {"status": "done", "output": f"Agent '{name}' created at {agent_dir}"}

    def _handle_trace(self, args: dict) -> dict:
        """Handle trace subcommands."""
        from core.memory import get_recent_traces, get_trace_by_id

        sub = args.get("subcmd", "list")
        if sub == "list":
            traces = get_recent_traces(args.get("limit", 20))
            return {"status": "done", "output": traces}
        elif sub == "show":
            trace_id = args.get("trace_id")
            trace = get_trace_by_id(trace_id)
            return {"status": "done", "output": trace}
        return {"status": "error", "output": "Unknown trace subcommand"}

    def _handle_schedule(self, args: dict) -> dict:
        """Handle schedule subcommands."""
        from core.memory import add_schedule, get_schedules, delete_schedule

        sub = args.get("subcmd", "list")
        if sub == "add":
            job_id = add_schedule(
                cron=args["cron"],
                agent=args["agent"],
                task=json.loads(args["task_json"]),
            )
            return {"status": "done", "output": f"Schedule added: job {job_id}"}
        elif sub == "list":
            schedules = get_schedules()
            return {"status": "done", "output": schedules}
        elif sub == "delete":
            delete_schedule(args["job_id"])
            return {"status": "done", "output": f"Deleted job {args['job_id']}"}
        return {"status": "error", "output": "Unknown schedule subcommand"}

    def _handle_status(self) -> dict:
        """System status."""
        registry_path = self.agents_dir / "registry.json"
        agent_count = 0
        if registry_path.exists():
            with open(registry_path) as f:
                agent_count = len(json.load(f))

        loaded = len(self._loaded_agents)
        awake = sum(1 for a in self._loaded_agents.values() if a.alive)

        return {
            "status": "done",
            "output": {
                "agents_registered": agent_count,
                "agents_loaded": loaded,
                "agents_awake": awake,
                "uptime": "running",
                "kage_dir": str(KAGE_DIR),
            },
        }


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\n[KAGE] Shutting down...")
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
    sys.exit(0)


def main():
    """Main entry point — daemon or one-shot command."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Check if already running
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            # Check if process is alive
            os.kill(pid, 0)
            print(f"[KAGE] Already running (PID {pid}). Use 'kage' CLI to interact.")
            return
        except (ProcessLookupError, ValueError):
            # Stale lock file
            LOCK_FILE.unlink()

    # Write PID
    LOCK_FILE.write_text(str(os.getpid()))

    kage = Kage()
    kage.init_context()
    kage.log("KAGE supervisor started")

    # Process command from argv first (regardless of tty)
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        result = kage.process_command(cmd, args)
        print(json.dumps(result, indent=2, default=str))
        # CLI command done — clean up lock and exit
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
        kage.log("KAGE supervisor stopped")
        return

    # If piped stdin, also read commands from pipe
    elif not sys.stdin.isatty():
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                cmd = json.loads(line)
                result = kage.process_command(cmd["command"], cmd.get("args", {}))
                print(json.dumps(result))
        except (EOFError, json.JSONDecodeError):
            pass
    else:
        print("[KAGE] Supervisor running. Use 'kage' CLI to interact.")

    # Cleanup
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
    kage.log("KAGE supervisor stopped")


if __name__ == "__main__":
    main()