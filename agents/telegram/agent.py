#!/usr/bin/env python3
"""
Telegram Agent — Native Telegram Bot Integration for KAGE OS.
Connects Kage Brain to Telegram bot (@Mini_kage_bot) with continuous long-polling,
user-keyed persistent memory injection (~/.kage/memory.json), command handling, and tool output execution.
"""

import gc
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

PID_FILE = Path.home() / ".kage" / "telegram.pid"


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False
        self.bot_token = ""
        self.api_base = ""
        self.running = False
        self.last_update_id = 0

    def wake(self, task_data: dict) -> dict:
        """Wake up: load token and connection parameters."""
        global requests
        import requests as _requests
        requests = _requests

        config_path = Path(__file__).parent.parent.parent / "config.toml"
        user_config_path = Path.home() / ".kage" / "config.toml"

        config = {}
        for p in [config_path, user_config_path]:
            if p.exists():
                cfg = self._load_config(p)
                config.update(cfg)

        tg_config = config.get("telegram", {})
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or tg_config.get(
            "bot_token", "8819096503:AAEqOGM_9y7MbWTLa-5Ds5MBQfxQtiD3XKs"
        )
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"

        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        action = task_data.get("action", "poll")
        chat_id = task_data.get("chat_id", task_data.get("to", ""))
        text = task_data.get("text", task_data.get("message", ""))

        try:
            if action in ("poll", "start", "listen"):
                self.start_polling()
                return {"status": "done", "output": "Telegram polling stopped cleanly"}

            elif action in ("send_message", "send"):
                if not chat_id or not text:
                    return {"status": "error", "output": "Missing 'chat_id' or 'text' parameter"}
                res = self._send_message(chat_id, text)
                return {"status": "done", "output": res}

            elif action == "status":
                status = self._get_status()
                return {"status": "done", "output": status}

            else:
                return {"status": "error", "output": f"Unknown action: {action}"}

        except Exception as e:
            return {"status": "error", "output": str(e)}

    def _get_status(self) -> Dict:
        """Check Telegram bot status with getMe endpoint."""
        resp = requests.get(f"{self.api_base}/getMe", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            bot_info = data.get("result", {})
            return {
                "status": "connected",
                "bot_id": bot_info.get("id"),
                "bot_name": bot_info.get("first_name"),
                "username": f"@{bot_info.get('username')}",
            }
        return {"status": "error", "message": "Failed getMe query"}

    def _send_message(self, chat_id: Union[int, str], text: str) -> Dict:
        """Send message via Telegram API."""
        url = f"{self.api_base}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code != 200:
            payload.pop("parse_mode", None)
            resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def start_polling(self):
        """Continuous long-polling loop for incoming messages."""
        self.running = True
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))

        print(f"[TELEGRAM AGENT] Long polling active for @Mini_kage_bot (PID {os.getpid()})...")

        while self.running:
            try:
                url = f"{self.api_base}/getUpdates"
                params = {"offset": self.last_update_id + 1, "timeout": 20}
                resp = requests.get(url, params=params, timeout=30)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        for update in data.get("result", []):
                            self.last_update_id = max(self.last_update_id, update["update_id"])
                            self._handle_update(update)
                elif resp.status_code in (401, 404):
                    print(f"[TELEGRAM AGENT] Invalid bot token. Polling aborted.")
                    break
                else:
                    time.sleep(5)

            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.ConnectionError:
                time.sleep(5)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[TELEGRAM AGENT] Error in polling loop: {e}", file=sys.stderr)
                time.sleep(3)

        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except Exception:
                pass

    def _handle_update(self, update: Dict):
        """Process incoming update object with per-user persistent memory context."""
        message = update.get("message") or update.get("edited_message")
        if not message or "text" not in message:
            return

        chat_id = str(message["chat"]["id"])
        sender = message.get("from", {}).get("first_name", "User")
        text = message.get("text", "").strip()

        start_time = time.time()
        reply_text = ""
        agent_output_text = ""

        try:
            if text in ("/start", "/help"):
                reply_text = (
                    f"👋 *Welcome to KAGE OS Bot, {sender}!*\n\n"
                    "I am your personal AI Operating System assistant running on Termux.\n\n"
                    "Available Commands:\n"
                    "• `/status` — System & supervisor status\n"
                    "• `/health` — Phone telemetry\n"
                    "• `/agents` — List personal domain agents\n\n"
                    "I automatically remember details about you across chats! Try saying:\n"
                    "_'My name is Alex'_ or _'Remember that I like Python'_."
                )

            elif text == "/status":
                status_res = self.context.brain.process_command("status", {})
                out = status_res.get("output", {})
                reply_text = (
                    "📊 *KAGE OS Status*\n"
                    f"• Agents Registered: {out.get('agents_registered', 0)}\n"
                    f"• Features Active: Browser, OpenHands, MCP, CrewAI, Persistent Memory\n"
                    f"• Active Schedules: {out.get('scheduled_jobs', 0)}\n"
                    f"• Status: ONLINE"
                )

            elif text == "/health":
                health_res = self.context.brain.process_command("health", {})
                out = health_res.get("output", {})
                bat = out.get("battery", {})
                stor = out.get("storage", {})
                reply_text = (
                    "📱 *Phone Telemetry*\n"
                    f"• Battery: {bat.get('percentage', '100')}% ({bat.get('status', 'normal')})\n"
                    f"• Storage: {stor.get('used', '?')} / {stor.get('total', '?')}\n"
                    f"• Uptime: {out.get('uptime', 'unknown')}"
                )

            elif text == "/agents":
                agents_res = self.context.brain.process_command("agent", {"subcmd": "list"})
                agents_list = agents_res.get("output", [])
                lines = ["🤖 *Registered KAGE Agents:*"]
                for a in agents_list:
                    lines.append(f"• `{a['name']}` ({a['status']}) — {a.get('description', '')}")
                reply_text = "\n".join(lines)

            else:
                # Dispatch query with user_id key for persistent memory lookup
                chat_res = self.context.brain.process_command("chat", {"message": text, "user_id": chat_id})
                reply_text = chat_res.get("response") or chat_res.get("brain_response") or "Instruction complete."

                if "agent_result" in chat_res and chat_res["agent_result"]:
                    ag_res = chat_res["agent_result"]
                    output_payload = ag_res.get("output", {})
                    if isinstance(output_payload, (dict, list)):
                        agent_output_text = json.dumps(output_payload, indent=2, default=str)
                    else:
                        agent_output_text = str(output_payload)

            self._send_message(chat_id, reply_text)

            if agent_output_text:
                formatted_out = f"⚙️ *Execution Output:*\n```json\n{agent_output_text[:3000]}\n```"
                self._send_message(chat_id, formatted_out)

            duration_ms = (time.time() - start_time) * 1000
            try:
                from core.memory import log_trace
                log_trace(
                    agent="telegram",
                    task={"chat_id": chat_id, "user": sender, "text": text},
                    output={"reply": reply_text, "execution_output": agent_output_text},
                    duration_ms=duration_ms,
                )
            except Exception:
                pass

        except Exception as e:
            err_msg = f"❌ Error processing command: {e}"
            print(f"[TELEGRAM AGENT] Error handling update: {e}", file=sys.stderr)
            try:
                self._send_message(chat_id, err_msg)
            except Exception:
                pass

    def sleep(self):
        """Clean shutdown of polling loop."""
        self.running = False
        self.alive = False
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except Exception:
                pass
        gc.collect()

    @staticmethod
    def _load_config(config_path: Path) -> Dict:
        try:
            import toml
            return toml.load(config_path)
        except ImportError:
            config = {}
            current_section = None
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        current_section = line[1:-1]
                        config[current_section] = {}
                    elif "=" in line and current_section:
                        key, _, val = line.partition("=")
                        config[current_section][key.strip()] = val.strip().strip('"\'')
            return config


if __name__ == "__main__":
    KAGE_ROOT = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(KAGE_ROOT))
    import kage
    sup = kage.Kage()
    sup.init_context()
    agent = Agent(sup.context)
    agent.wake({"action": "poll"})
