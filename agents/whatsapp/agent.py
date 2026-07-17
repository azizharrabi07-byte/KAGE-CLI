#!/usr/bin/env python3
"""
WhatsApp Agent — Spawns Node.js Baileys bridge, sends/reads messages.
Bridge runs on localhost:3030. Only alive during wake().
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

# Lazy imports


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False
        self.process = None
        self.bridge_url = "http://localhost:3030"
        self.bridge_dir = Path(__file__).parent / "bridge"

    def wake(self, task_data: dict) -> dict:
        """Wake up: start bridge if needed, then execute."""
        # Lazy import
        global requests
        import requests as _requests
        requests = _requests

        # Start bridge if not running
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
            else:
                return {"status": "error", "output": f"Unknown action: {action}"}
        except Exception as e:
            return {"status": "error", "output": str(e)}

    def _send(self, task_data: dict) -> dict:
        """Send a WhatsApp message."""
        to = task_data.get("to", "")
        text = task_data.get("text", "")

        if not to or not text:
            return {"status": "error", "output": "Missing 'to' or 'text'"}

        # Ask permission
        approved = self.context.permissions.require_approval(
            "whatsapp.send",
            f"Send WhatsApp to {to}: {text[:50]}..."
        )
        if not approved:
            return {"status": "denied", "output": "Send denied by user"}

        resp = requests.post(
            f"{self.bridge_url}/send",
            json={"to": to, "text": text},
            timeout=10,
        )
        result = resp.json()
        return {"status": "done", "output": result}

    def _read(self) -> dict:
        """Read unread messages."""
        resp = requests.get(f"{self.bridge_url}/read", timeout=10)
        return {"status": "done", "output": resp.json()}

    def _status(self) -> dict:
        """Check WhatsApp connection status."""
        resp = requests.get(f"{self.bridge_url}/status", timeout=5)
        return {"status": "done", "output": resp.json()}

    def _ensure_bridge(self):
        """Start the Node.js bridge if not already running."""
        # Check if bridge is alive
        try:
            resp = requests.get(f"{self.bridge_url}/health", timeout=2)
            if resp.status_code == 200:
                return  # Already running
        except Exception:
            pass

        # Check if node_modules exist
        if not (self.bridge_dir / "node_modules").exists():
            self.log("Installing bridge dependencies...")
            subprocess.run(
                ["npm", "install"],
                cwd=str(self.bridge_dir),
                capture_output=True,
                timeout=120,
            )

        # Start bridge
        self.process = subprocess.Popen(
            ["node", "index.js"],
            cwd=str(self.bridge_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for bridge to start
        for _ in range(10):
            time.sleep(1)
            try:
                resp = requests.get(f"{self.bridge_url}/health", timeout=2)
                if resp.status_code == 200:
                    self.log("Bridge started")
                    return
            except Exception:
                pass

        self.log("Warning: Bridge may not have started properly")

    def log(self, msg: str):
        print(f"[WHATSAPP] {msg}", file=sys.stderr)

    def sleep(self):
        """Stop bridge and clean up."""
        self.alive = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        # Unload modules
        for mod in list(sys.modules.keys()):
            if mod.startswith("requests"):
                del sys.modules[mod]
        gc.collect()