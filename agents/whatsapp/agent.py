#!/usr/bin/env python3
"""
WhatsApp Agent — Spawns Node.js Baileys bridge, sends/reads messages.
Bridge runs as persistent background microservice on localhost:3030.
"""

import gc
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False
        self.bridge_url = "http://localhost:3030"
        self.bridge_dir = Path(__file__).parent / "bridge"

    def wake(self, task_data: dict) -> dict:
        """Wake up: start bridge if needed, then execute task."""
        global requests
        import requests as _requests
        requests = _requests

        self._ensure_bridge()

        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        action = task_data.get("action", "status")

        try:
            if action == "send":
                return self._send(task_data)
            elif action == "read":
                return self._read()
            elif action == "status":
                return self._status()
            elif action == "stop":
                return self._stop_bridge()
            else:
                return {"status": "error", "output": f"Unknown action: {action}"}
        except Exception as e:
            return {"status": "error", "output": str(e)}

    def _send(self, task_data: dict) -> dict:
        """Send a WhatsApp message."""
        to = task_data.get("to", "")
        text = task_data.get("text", "")

        if not to or not text:
            return {"status": "error", "output": "Missing 'to' or 'text' parameter"}

        approved = self.context.permissions.require_approval(
            "whatsapp.send",
            f"Send WhatsApp message to {to}: {text[:50]}..."
        )
        if not approved:
            return {"status": "denied", "output": "Send denied by user"}

        resp = requests.post(
            f"{self.bridge_url}/send",
            json={"to": to, "text": text},
            timeout=15,
        )
        return {"status": "done", "output": resp.json()}

    def _read(self) -> dict:
        """Read unread/buffered messages."""
        resp = requests.get(f"{self.bridge_url}/read", timeout=10)
        return {"status": "done", "output": resp.json()}

    def _status(self) -> dict:
        """Check WhatsApp connection status."""
        resp = requests.get(f"{self.bridge_url}/status", timeout=5)
        return {"status": "done", "output": resp.json()}

    def _stop_bridge(self) -> dict:
        """Stop the Node.js bridge service."""
        try:
            requests.post(f"{self.bridge_url}/stop", timeout=2)
            return {"status": "done", "output": "WhatsApp bridge stopped"}
        except Exception as e:
            return {"status": "done", "output": f"Bridge already stopped or failed to stop: {e}"}

    def _ensure_bridge(self):
        """Start the Node.js bridge in background if not running."""
        try:
            resp = requests.get(f"{self.bridge_url}/health", timeout=2)
            if resp.status_code == 200:
                return
        except Exception:
            pass

        if not (self.bridge_dir / "node_modules").exists():
            self.log("Installing bridge dependencies...")
            subprocess.run(
                ["npm", "install"],
                cwd=str(self.bridge_dir),
                capture_output=True,
                timeout=120,
            )

        self.log("Starting WhatsApp bridge process...")
        subprocess.Popen(
            ["node", "index.js"],
            cwd=str(self.bridge_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        for _ in range(10):
            time.sleep(1)
            try:
                resp = requests.get(f"{self.bridge_url}/health", timeout=2)
                if resp.status_code == 200:
                    self.log("WhatsApp bridge active")
                    return
            except Exception:
                pass

        self.log("Warning: Bridge process may still be starting up")

    def log(self, msg: str):
        print(f"[WHATSAPP] {msg}", file=sys.stderr)

    def sleep(self):
        """Keep persistent bridge process running in background for persistent connection."""
        self.alive = False
        gc.collect()
