#!/usr/bin/env python3
"""
web_ui.py — Web Dashboard & Server for KAGE OS.
Exposes modern landing page / control dashboard on http://localhost:8080.
Inspired by OpenCode / OpenClaude / OpenHands UI.
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any

KAGE_DIR = Path(__file__).parent.parent
WEB_DIR = KAGE_DIR / "web"


class KageWebHandler(BaseHTTPRequestHandler):
    supervisor = None  # Reference to Kage supervisor

    def log_message(self, format, *args):
        # Suppress standard HTTP request logging
        pass

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/" or path == "/index.html":
            html_file = WEB_DIR / "index.html"
            if html_file.exists():
                content = html_file.read_bytes()
                self._send_response(200, "text/html", content)
            else:
                self._send_json(404, {"error": "Dashboard template not found"})

        elif path == "/api/status":
            res = self.supervisor.process_command("status", {})
            self._send_json(200, res)

        elif path == "/api/health":
            res = self.supervisor.process_command("health", {})
            self._send_json(200, res)

        elif path == "/api/agents":
            res = self.supervisor.process_command("agent", {"subcmd": "list"})
            self._send_json(200, res)

        elif path == "/api/traces":
            res = self.supervisor.process_command("trace", {"subcmd": "list", "limit": 30})
            self._send_json(200, res)

        elif path == "/api/schedules":
            res = self.supervisor.process_command("schedule", {"subcmd": "list"})
            self._send_json(200, res)

        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        if self.path == "/api/chat":
            msg = data.get("message", "")
            res = self.supervisor.process_command("chat", {"message": msg})
            self._send_json(200, res)

        elif self.path == "/api/wake":
            agent_name = data.get("agent", "")
            task_data = data.get("task", {})
            res = self.supervisor.wake(agent_name, task_data)
            self._send_json(200, res)

        else:
            self._send_json(404, {"error": "Unknown POST route"})

    def _send_response(self, status_code: int, content_type: str, body: bytes):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status_code: int, payload: Dict[str, Any]):
        json_data = json.dumps(payload, default=str).encode("utf-8")
        self._send_response(status_code, "application/json", json_data)


def run_server(port: int = 8080):
    """Run KAGE Web Server."""
    sys.path.insert(0, str(KAGE_DIR))
    import kage
    supervisor = kage.Kage()
    supervisor.init_context()

    KageWebHandler.supervisor = supervisor

    server_address = ("", port)
    httpd = HTTPServer(server_address, KageWebHandler)
    print(f"🌐 KAGE OS Dashboard running on http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping KAGE Web Server...")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
