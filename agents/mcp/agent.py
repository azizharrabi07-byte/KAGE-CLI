#!/usr/bin/env python3
"""
MCP Agent — Model Context Protocol Client Bridge for KAGE OS.
Connects Kage to remote and local MCP tool/resource servers (JSON-RPC 2.0 over HTTP/SSE/Stdio).
Reference: https://github.com/punkpeye/awesome-mcp-servers
"""

import gc
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False
        self.servers = []

    def wake(self, task_data: dict) -> dict:
        """Wake up: load MCP configuration and libraries."""
        global requests
        import requests as _requests
        requests = _requests

        config_path = Path(__file__).parent.parent.parent / "config.toml"
        user_config_path = Path.home() / ".kage" / "config.toml"

        config = {}
        if config_path.exists():
            config = self._load_config(config_path)
        if user_config_path.exists():
            user_cfg = self._load_config(user_config_path)
            config.update(user_cfg)

        mcp_config = config.get("mcp", {})
        servers_val = mcp_config.get("servers", [
            {"name": "fetch", "url": "http://localhost:8000/mcp"},
            {"name": "filesystem", "url": "http://localhost:8001/mcp"},
        ])

        if isinstance(servers_val, str):
            try:
                servers_val = json.loads(servers_val)
            except Exception:
                servers_val = []

        self.servers = servers_val if isinstance(servers_val, list) else []

        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        action = task_data.get("action", "list_servers")
        server_name = task_data.get("server", "")
        tool_name = task_data.get("tool", "")
        arguments = task_data.get("args", task_data.get("arguments", {}))
        uri = task_data.get("uri", "")

        try:
            if action == "list_servers":
                return {"status": "done", "output": self.servers}

            elif action == "list_tools":
                server = self._find_server(server_name)
                if not server:
                    return {"status": "error", "output": f"Server '{server_name}' not found in configuration."}
                result = self._rpc_call(server["url"], "tools/list", {})
                return {"status": "done", "output": result}

            elif action == "call_tool":
                if not tool_name:
                    return {"status": "error", "output": "Missing 'tool' parameter"}
                server = self._find_server(server_name)
                if not server:
                    return {"status": "error", "output": f"Server '{server_name}' not found in configuration."}

                approved = self.context.permissions.require_approval(
                    f"mcp.call_tool.{tool_name}",
                    f"Execute MCP Tool '{tool_name}' on server '{server['name']}'"
                )
                if not approved:
                    return {"status": "denied", "output": f"Tool execution '{tool_name}' denied by user"}

                result = self._rpc_call(server["url"], "tools/call", {"name": tool_name, "arguments": arguments})
                return {"status": "done", "output": result}

            elif action == "list_resources":
                server = self._find_server(server_name)
                if not server:
                    return {"status": "error", "output": f"Server '{server_name}' not found."}
                result = self._rpc_call(server["url"], "resources/list", {})
                return {"status": "done", "output": result}

            elif action == "read_resource":
                if not uri:
                    return {"status": "error", "output": "Missing 'uri' parameter"}
                server = self._find_server(server_name)
                if not server:
                    return {"status": "error", "output": f"Server '{server_name}' not found."}
                result = self._rpc_call(server["url"], "resources/read", {"uri": uri})
                return {"status": "done", "output": result}

            else:
                return {"status": "error", "output": f"Unknown action: {action}"}

        except requests.exceptions.ConnectionError as e:
            return {
                "status": "error",
                "output": f"Cannot connect to MCP server: {e}"
            }
        except Exception as e:
            return {"status": "error", "output": str(e)}

    def _find_server(self, name: str) -> Optional[Dict]:
        if not self.servers:
            return None
        if not name and len(self.servers) > 0:
            return self.servers[0]
        for s in self.servers:
            if isinstance(s, dict) and (s.get("name") == name or s.get("url") == name):
                return s
        return None

    def _rpc_call(self, url: str, method: str, params: Dict) -> Dict:
        """Issue a JSON-RPC 2.0 call to an MCP server endpoint."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"MCP RPC Error: {data['error']}")
        return data.get("result", {})

    def sleep(self):
        self.alive = False
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
