#!/usr/bin/env python3
"""
MCP Protocol Feature — Model Context Protocol Client Bridge for KAGE OS.
Available to all agents and brain via context.mcp
Reference: https://github.com/punkpeye/awesome-mcp-servers
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class MCPFeature:
    """Built-in Model Context Protocol Engine."""

    def __init__(self, context=None):
        self.context = context
        self.servers = self._load_servers()

    def _load_servers(self) -> List[Dict]:
        config_path = Path(__file__).parent.parent.parent / "config.toml"
        user_config_path = Path.home() / ".kage" / "config.toml"

        config = {}
        for p in [config_path, user_config_path]:
            if p.exists():
                try:
                    import toml
                    config.update(toml.load(p))
                except Exception:
                    pass

        mcp_cfg = config.get("mcp", {})
        servers_val = mcp_cfg.get("servers", [
            {"name": "fetch", "url": "http://localhost:8000/mcp"},
            {"name": "filesystem", "url": "http://localhost:8001/mcp"}
        ])

        if isinstance(servers_val, str):
            try:
                servers_val = json.loads(servers_val)
            except Exception:
                servers_val = []

        return servers_val if isinstance(servers_val, list) else []

    def list_servers(self) -> List[Dict]:
        return self.servers

    def list_tools(self, server_name: str = "") -> Dict:
        server = self._find_server(server_name)
        if not server:
            return {"error": f"Server '{server_name}' not configured"}
        return self._rpc_call(server["url"], "tools/list", {})

    def call_tool(self, server_name: str, tool_name: str, args: Dict) -> Dict:
        server = self._find_server(server_name)
        if not server:
            return {"error": f"Server '{server_name}' not configured"}

        if self.context and hasattr(self.context, "permissions"):
            approved = self.context.permissions.require_approval(
                f"mcp.call_tool.{tool_name}",
                f"Call tool '{tool_name}' on server '{server['name']}'"
            )
            if not approved:
                return {"status": "denied", "output": "Tool execution denied"}

        return self._rpc_call(server["url"], "tools/call", {"name": tool_name, "arguments": args})

    def list_resources(self, server_name: str = "") -> Dict:
        server = self._find_server(server_name)
        if not server:
            return {"error": f"Server '{server_name}' not configured"}
        return self._rpc_call(server["url"], "resources/list", {})

    def read_resource(self, server_name: str, uri: str) -> Dict:
        server = self._find_server(server_name)
        if not server:
            return {"error": f"Server '{server_name}' not configured"}
        return self._rpc_call(server["url"], "resources/read", {"uri": uri})

    def _find_server(self, name: str) -> Optional[Dict]:
        if not self.servers:
            return None
        if not name:
            return self.servers[0]
        for s in self.servers:
            if isinstance(s, dict) and (s.get("name") == name or s.get("url") == name):
                return s
        return None

    def _rpc_call(self, url: str, method: str, params: Dict) -> Dict:
        import requests
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"MCP RPC Error: {data['error']}")
        return data.get("result", {})
