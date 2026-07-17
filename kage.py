#!/usr/bin/env python3
"""
kage.py — Main daemon / supervisor loop & IPC server with multi-step ReAct agent feedback loop.
Hosts background scheduler, auto-spawns background services (Telegram bot),
executes core OS features (Browser-Use, OpenHands, MCP, CrewAI, Memory), and logs supervisor events to kage.log.
"""

import json
import os
import sys
import time
import socket
import signal
import threading
import subprocess
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any

KAGE_DIR = Path(__file__).parent
KAGE_HOME = Path.home() / ".kage"
KAGE_HOME.mkdir(parents=True, exist_ok=True)

KAGE_OS_DIR = Path.home() / "kage-os"

LOCK_FILE = KAGE_HOME / "kage.pid"
SOCKET_FILE = KAGE_HOME / "kage.sock"
TELEGRAM_PID_FILE = KAGE_HOME / "telegram.pid"


def resolve_log_file() -> Path:
    if KAGE_OS_DIR.exists():
        return KAGE_OS_DIR / "kage.log"
    return KAGE_HOME / "kage.log"

LOG_FILE = resolve_log_file()


class Kage:
    """The supervisor brain. Wakes agents, manages state, and exposes core features."""

    def __init__(self):
        self.running = True
        self.agents_dir = KAGE_DIR / "agents"
        self.context = None
        self._loaded_agents = {}
        self.scheduler = None

    def log(self, msg: str, level: str = "INFO"):
        """Log structured timestamped messages to log files."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] {msg}"

        log_paths = [LOG_FILE, KAGE_HOME / "kage.log"]
        if KAGE_OS_DIR.exists():
            log_paths.append(KAGE_OS_DIR / "kage.log")

        seen_paths = set()
        for lp in log_paths:
            if str(lp) in seen_paths:
                continue
            seen_paths.add(str(lp))
            try:
                lp.parent.mkdir(parents=True, exist_ok=True)
                with open(lp, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass

    def init_context(self):
        """Initialize shared context (brain, memory, permissions, user_memory, and core features)."""
        from core import memory, permissions, scheduler, user_memory
        from core.features import BrowserFeature, OpenHandsFeature, MCPFeature, CrewFeature

        ctx = type("Context", (), {
            "brain": self,
            "memory": memory,
            "user_memory": user_memory,
            "permissions": permissions,
            "browser": BrowserFeature(),
            "openhands": OpenHandsFeature(),
            "mcp": MCPFeature(),
            "crew": CrewFeature(),
        })()

        ctx.openhands.context = ctx
        ctx.mcp.context = ctx
        ctx.crew.context = ctx

        self.context = ctx
        memory.init_db()

        self.scheduler = scheduler.Scheduler(wake_fn=self.wake)
        self._load_schedules_into_scheduler()
        self.scheduler.start()

        self.ensure_telegram_bot_daemon()

        self.log("Context, core features, user memory engine, and scheduler initialized")

    def ensure_telegram_bot_daemon(self):
        """Ensure Telegram bot polling daemon is running if configured."""
        if TELEGRAM_PID_FILE.exists():
            try:
                pid = int(TELEGRAM_PID_FILE.read_text().strip())
                os.kill(pid, 0)
                return
            except Exception:
                try:
                    TELEGRAM_PID_FILE.unlink()
                except Exception:
                    pass

        tg_agent_py = self.agents_dir / "telegram" / "agent.py"
        if tg_agent_py.exists():
            try:
                proc = subprocess.Popen(
                    [sys.executable, str(tg_agent_py)],
                    cwd=str(KAGE_DIR),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                TELEGRAM_PID_FILE.write_text(str(proc.pid))
                self.log(f"Spawned background Telegram bot process (PID {proc.pid})")
            except Exception as e:
                self.log(f"Failed starting Telegram bot daemon: {e}", "ERROR")

    def _load_schedules_into_scheduler(self):
        if not self.scheduler or not self.context:
            return
        try:
            schedules = self.context.memory.get_schedules()
            for job in schedules:
                try:
                    task = json.loads(job["task_json"]) if isinstance(job["task_json"], str) else job["task_json"]
                    self.scheduler.add_job(
                        job_id=job["id"],
                        cron=job["cron"],
                        agent=job["agent"],
                        task=task,
                    )
                except Exception as e:
                    self.log(f"Failed to parse schedule job {job.get('id')}: {e}", "ERROR")
        except Exception as e:
            self.log(f"Failed to load schedules: {e}", "ERROR")

    def load_agent(self, agent_name: str):
        if agent_name in self._loaded_agents:
            return self._loaded_agents[agent_name]

        registry_path = self.agents_dir / "registry.json"
        if not registry_path.exists():
            self.log("Registry not found", "ERROR")
            return None

        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception as e:
            self.log(f"Error reading registry: {e}", "ERROR")
            return None

        if agent_name not in registry:
            self.log(f"Agent '{agent_name}' not in registry", "ERROR")
            return None

        agent_info = registry[agent_name]
        agent_path = self.agents_dir / agent_info["path"]
        agent_py = agent_path / "agent.py"

        if not agent_py.exists():
            self.log(f"Agent file not found: {agent_py}", "ERROR")
            return None

        try:
            spec = importlib.util.spec_from_file_location(
                f"agents.{agent_name}", str(agent_py)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            agent_instance = module.Agent(self.context)
            self._loaded_agents[agent_name] = agent_instance
            return agent_instance
        except Exception as e:
            self.log(f"Error loading agent '{agent_name}': {e}", "ERROR")
            return None

    def wake(self, agent_name: str, task_data: dict) -> dict:
        self.log(f"Waking agent: {agent_name}")

        agent = self.load_agent(agent_name)
        if not agent:
            return {"status": "error", "output": f"Agent '{agent_name}' not found"}

        start_time = time.time()
        result = {}
        try:
            result = agent.wake(task_data)
        except Exception as e:
            result = {"status": "error", "output": str(e)}
            self.log(f"Agent {agent_name} error: {e}", "ERROR")
        finally:
            duration_ms = (time.time() - start_time) * 1000

            try:
                from core.memory import log_trace
                log_trace(
                    agent=agent_name,
                    task=task_data,
                    output=result.get("output") if result.get("status") == "done" else result,
                    error=result.get("output") if result.get("status") == "error" else None,
                    duration_ms=duration_ms,
                )
            except Exception as e:
                self.log(f"Trace logging failed: {e}", "ERROR")

            self.log(f"Agent {agent_name} finished in {duration_ms:.0f}ms")

        return result

    def process_command(self, command: str, args: dict) -> dict:
        if command == "chat":
            return self._handle_chat(args.get("message", ""), user_id=args.get("user_id", "default"))
        elif command == "agent":
            return self._handle_agent_command(args)
        elif command == "features":
            return self._handle_features_command(args)
        elif command == "trace":
            return self._handle_trace(args)
        elif command == "health":
            return self.wake("system", {})
        elif command == "schedule":
            return self._handle_schedule(args)
        elif command == "status":
            return self._handle_status()
        elif command == "stop":
            self.running = False
            return {"status": "done", "output": "KAGE supervisor shutting down"}
        else:
            return {"status": "error", "output": f"Unknown command: {command}"}

    def _execute_action_payload(self, action_type: str, task_data: dict, user_id: str = "default") -> dict:
        """Execute feature, memory, or agent action and return structured output."""
        if action_type == "browser":
            fn = task_data.get("action", "search")
            if fn == "search":
                res = self.context.browser.search(task_data.get("query", ""))
            else:
                res = self.context.browser.fetch(task_data.get("url", task_data.get("query", "")))
            return {"status": "done", "output": res}

        elif action_type == "openhands":
            fn = task_data.get("action", "execute_cmd")
            if fn in ("execute_cmd", "cmd"):
                res = self.context.openhands.execute_cmd(task_data.get("command", ""))
            elif fn == "run_python":
                res = self.context.openhands.run_python(task_data.get("code", ""))
            else:
                res = self.context.openhands.write_code(task_data.get("path", ""), task_data.get("content", ""))
            return {"status": "done", "output": res}

        elif action_type == "mcp":
            fn = task_data.get("action", "list_servers")
            if fn == "list_servers":
                res = self.context.mcp.list_servers()
            else:
                res = self.context.mcp.call_tool(task_data.get("server", ""), task_data.get("tool", ""), task_data.get("args", {}))
            return {"status": "done", "output": res}

        elif action_type == "crew":
            res = self.context.crew.run_crew(
                crew_agents=task_data.get("agents", []),
                tasks=task_data.get("tasks", []),
                template=task_data.get("template", ""),
                topic=task_data.get("topic", "")
            )
            return {"status": "done", "output": res}

        elif action_type == "memory":
            from core import user_memory
            uid = task_data.get("user_id", user_id)
            name = task_data.get("name")
            fact = task_data.get("fact")
            key = task_data.get("key")
            val = task_data.get("value")

            saved_items = []
            if name:
                user_memory.set_user_name(uid, name)
                saved_items.append(f"name = '{name}'")
            if fact:
                user_memory.add_user_fact(uid, fact)
                saved_items.append(f"fact = '{fact}'")
            if key and val is not None:
                user_memory.set_user_kv(uid, key, val)
                saved_items.append(f"{key} = '{val}'")

            msg = f"Stored memory for user '{uid}': " + ", ".join(saved_items) if saved_items else f"Updated memory for user '{uid}'"
            return {"status": "done", "output": msg}

        else:
            return self.wake(action_type, task_data)

    def _handle_chat(self, message: str, user_id: str = "default") -> dict:
        """Route message through brain with user memory context and multi-turn ReAct loop."""
        from core.brain import call_llm, extract_action_json, KAGE_SYSTEM_PROMPT

        messages = [{"role": "user", "content": message}]
        max_turns = 3
        last_action_result = None

        for turn in range(max_turns):
            llm_res = call_llm(messages=messages, system=KAGE_SYSTEM_PROMPT, user_id=user_id)
            content = llm_res.get("content", "")

            action = extract_action_json(content)
            if not action:
                return {
                    "status": "done",
                    "input": message,
                    "response": content,
                    "agent_result": last_action_result
                }

            action_type = action.get("action", "")
            task_data = action.get("task", {})

            last_action_result = self._execute_action_payload(action_type, task_data, user_id=user_id)

            messages.append({"role": "assistant", "content": content})
            tool_output_str = json.dumps(last_action_result.get("output", last_action_result), default=str)
            messages.append({
                "role": "user",
                "content": f"[Observation from {action_type} execution]: {tool_output_str[:3000]}\n\nSummarize result or execute next step if needed."
            })

        return {
            "status": "done",
            "input": message,
            "response": content,
            "agent_result": last_action_result
        }

    def _handle_features_command(self, args: dict) -> dict:
        feat = args.get("feature", "")
        action = args.get("action", "")

        if feat == "browser":
            if action == "search":
                res = self.context.browser.search(args.get("query", ""))
            else:
                res = self.context.browser.fetch(args.get("url", ""))
            return {"status": "done", "output": res}

        elif feat == "openhands":
            if action in ("execute_cmd", "cmd"):
                res = self.context.openhands.execute_cmd(args.get("command", ""))
            elif action == "run_python":
                res = self.context.openhands.run_python(args.get("code", ""))
            else:
                res = self.context.openhands.write_code(args.get("path", ""), args.get("content", ""))
            return {"status": "done", "output": res}

        elif feat == "mcp":
            if action == "list_servers":
                res = self.context.mcp.list_servers()
            else:
                res = self.context.mcp.call_tool(args.get("server", ""), args.get("tool", ""), args.get("args", {}))
            return {"status": "done", "output": res}

        elif feat == "crew":
            res = self.context.crew.run_crew([], [], template=args.get("template", ""), topic=args.get("topic", ""))
            return {"status": "done", "output": res}

        return {"status": "error", "output": f"Unknown feature: {feat}"}

    def _handle_agent_command(self, args: dict) -> dict:
        sub = args.get("subcmd", "list")

        if sub == "list":
            registry_path = self.agents_dir / "registry.json"
            registry = {}
            if registry_path.exists():
                try:
                    with open(registry_path, "r", encoding="utf-8") as f:
                        registry = json.load(f)
                except Exception:
                    registry = {}

            result = []
            for name, info in registry.items():
                agent = self._loaded_agents.get(name)
                status = "awake" if agent and getattr(agent, "alive", False) else "sleeping"
                result.append({
                    "name": name,
                    "status": status,
                    "description": info.get("description", "")
                })
            return {"status": "done", "output": result}

        elif sub == "wake":
            agent_name = args.get("agent", "")
            task_data = args.get("task", {})
            if isinstance(task_data, str):
                try:
                    task_data = json.loads(task_data)
                except Exception:
                    task_data = {}
            return self.wake(agent_name, task_data)

        elif sub == "create":
            agent_name = args.get("name", "")
            if not agent_name or not agent_name.isalnum():
                return {"status": "error", "output": "Invalid agent name. Use alphanumeric characters."}
            return self._create_agent(agent_name)

        return {"status": "error", "output": f"Unknown agent subcommand: {sub}"}

    def _create_agent(self, name: str) -> dict:
        agent_dir = self.agents_dir / name
        agent_dir.mkdir(parents=True, exist_ok=True)

        agent_py = agent_dir / "agent.py"
        if not agent_py.exists():
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
        action = task_data.get("action", "default")
        return {{"status": "done", "output": f"Agent {name} executed action: {{action}}"}}

    def sleep(self):
        self.alive = False
        gc.collect()
''', encoding="utf-8")

        registry_path = self.agents_dir / "registry.json"
        registry = {}
        if registry_path.exists():
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            except Exception:
                registry = {}

        registry[name] = {
            "path": name,
            "timeout": 30,
            "description": f"Custom agent: {name}",
        }

        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=4)

        return {"status": "done", "output": f"Agent '{name}' created successfully at {agent_dir}"}

    def _handle_trace(self, args: dict) -> dict:
        from core.memory import get_recent_traces, get_trace_by_id

        sub = args.get("subcmd", "list")
        if sub == "list":
            limit = args.get("limit", 20)
            traces = get_recent_traces(limit)
            return {"status": "done", "output": traces}
        elif sub == "show":
            trace_id = args.get("trace_id")
            if not trace_id:
                return {"status": "error", "output": "Missing trace_id parameter"}
            trace = get_trace_by_id(int(trace_id))
            return {"status": "done", "output": trace}
        return {"status": "error", "output": "Unknown trace subcommand"}

    def _handle_schedule(self, args: dict) -> dict:
        from core.memory import add_schedule, get_schedules, delete_schedule

        sub = args.get("subcmd", "list")
        if sub == "add":
            cron = args.get("cron", "")
            agent = args.get("agent", "")
            raw_task = args.get("task_json", "{}")
            task = json.loads(raw_task) if isinstance(raw_task, str) else raw_task

            if not cron or not agent:
                return {"status": "error", "output": "Missing required parameters: cron, agent"}

            job_id = add_schedule(cron=cron, agent=agent, task=task)

            if self.scheduler:
                self.scheduler.add_job(job_id=job_id, cron=cron, agent=agent, task=task)

            return {"status": "done", "output": f"Schedule added: job ID {job_id}"}

        elif sub == "list":
            schedules = get_schedules()
            return {"status": "done", "output": schedules}

        elif sub == "delete":
            job_id = args.get("job_id")
            if not job_id:
                return {"status": "error", "output": "Missing job_id"}
            delete_schedule(int(job_id))
            if self.scheduler:
                self.scheduler.remove_job(int(job_id))
            return {"status": "done", "output": f"Deleted schedule job {job_id}"}

        return {"status": "error", "output": "Unknown schedule subcommand"}

    def _handle_status(self) -> dict:
        registry_path = self.agents_dir / "registry.json"
        agent_count = 0
        if registry_path.exists():
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    agent_count = len(json.load(f))
            except Exception:
                pass

        loaded = len(self._loaded_agents)
        awake = sum(1 for a in self._loaded_agents.values() if getattr(a, "alive", False))

        scheduled_jobs = len(self.scheduler.get_jobs()) if self.scheduler else 0

        return {
            "status": "done",
            "output": {
                "agents_registered": agent_count,
                "agents_loaded": loaded,
                "agents_awake": awake,
                "built_in_features": ["browser_use", "openhands_sandbox", "mcp_engine", "crewai_orchestrator", "user_memory"],
                "scheduled_jobs": scheduled_jobs,
                "uptime": "running",
                "kage_dir": str(KAGE_DIR),
            },
        }

    def shutdown(self):
        self.running = False
        if self.scheduler:
            self.scheduler.stop()
        if SOCKET_FILE.exists():
            try:
                SOCKET_FILE.unlink()
            except Exception:
                pass
        if LOCK_FILE.exists():
            try:
                LOCK_FILE.unlink()
            except Exception:
                pass
        if TELEGRAM_PID_FILE.exists():
            try:
                pid = int(TELEGRAM_PID_FILE.read_text().strip())
                os.kill(pid, signal.SIGTERM)
                TELEGRAM_PID_FILE.unlink()
            except Exception:
                pass
        self.log("KAGE supervisor stopped cleanly")


def is_socket_alive() -> bool:
    if not SOCKET_FILE.exists():
        return False
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(1.0)
        client.connect(str(SOCKET_FILE))
        client.sendall(json.dumps({"command": "status", "args": {}}).encode("utf-8") + b"\n")
        response = client.recv(4096)
        client.close()
        return len(response) > 0
    except Exception:
        return False


def send_to_daemon(command: str, args: dict) -> Optional[dict]:
    if not SOCKET_FILE.exists():
        return None
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(60.0)
        client.connect(str(SOCKET_FILE))
        payload = json.dumps({"command": command, "args": args}) + "\n"
        client.sendall(payload.encode("utf-8"))

        data = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            data += chunk
            if data.endswith(b"\n"):
                break
        client.close()
        return json.loads(data.decode("utf-8").strip())
    except Exception as e:
        return None


def run_ipc_server(kage: Kage):
    if SOCKET_FILE.exists():
        try:
            SOCKET_FILE.unlink()
        except Exception:
            pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(SOCKET_FILE))
    server.listen(10)
    server.settimeout(1.0)

    kage.log(f"IPC socket listening on {SOCKET_FILE}")

    def handle_client(conn, addr):
        try:
            conn.settimeout(30.0)
            buffer = b""
            while kage.running:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                if b"\n" in buffer:
                    line, _, _ = buffer.partition(b"\n")
                    req = json.loads(line.decode("utf-8"))
                    cmd = req.get("command", "")
                    args = req.get("args", {})
                    resp = kage.process_command(cmd, args)
                    conn.sendall(json.dumps(resp).encode("utf-8") + b"\n")
                    break
        except Exception as e:
            err_resp = {"status": "error", "output": str(e)}
            try:
                conn.sendall(json.dumps(err_resp).encode("utf-8") + b"\n")
            except Exception:
                pass
        finally:
            conn.close()

    while kage.running:
        try:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
        except socket.timeout:
            continue
        except Exception as e:
            if kage.running:
                kage.log(f"IPC server accept error: {e}", "ERROR")

    server.close()


def main():
    kage = Kage()

    def handle_shutdown(signum, frame):
        print("\n[KAGE] Shutting down supervisor...")
        kage.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "daemon":
            if is_socket_alive():
                print("[KAGE] Supervisor daemon is already running.")
                return
            LOCK_FILE.write_text(str(os.getpid()))
            kage.init_context()
            print("[KAGE] Starting supervisor daemon...")
            kage.log("Daemon started")
            try:
                run_ipc_server(kage)
            finally:
                kage.shutdown()
            return

        args = {}
        if len(sys.argv) > 2:
            try:
                args = json.loads(sys.argv[2])
            except Exception:
                args = {"raw_arg": sys.argv[2]}

        if is_socket_alive():
            daemon_result = send_to_daemon(cmd, args)
            if daemon_result is not None:
                print(json.dumps(daemon_result, indent=2, default=str))
                return

        kage.init_context()
        result = kage.process_command(cmd, args)
        print(json.dumps(result, indent=2, default=str))
        if kage.scheduler:
            kage.scheduler.stop()
        return

    elif not sys.stdin.isatty():
        if is_socket_alive():
            try:
                for line in sys.stdin:
                    line = line.strip()
                    if not line:
                        continue
                    req = json.loads(line)
                    res = send_to_daemon(req.get("command", ""), req.get("args", {}))
                    print(json.dumps(res))
                return
            except Exception:
                pass

        kage.init_context()
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                req = json.loads(line)
                res = kage.process_command(req.get("command", ""), req.get("args", {}))
                print(json.dumps(res))
        except (EOFError, json.JSONDecodeError):
            pass
        finally:
            if kage.scheduler:
                kage.scheduler.stop()
    else:
        print("Usage: kage <command> [json_args] or kage daemon")


if __name__ == "__main__":
    main()
