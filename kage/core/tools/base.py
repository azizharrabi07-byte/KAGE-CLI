"""core/tools/base.py — the Tool interface and registry.

Every tool declares metadata (name, description, schema), validates input,
and returns a structured dict result. The supervisor runs tools through the
registry with permission gating (see core/security.py).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolSchema:
    """Minimal JSON-schema-ish argument declaration for validation/docs."""

    required: List[str] = field(default_factory=list)
    optional: Dict[str, str] = field(default_factory=dict)  # name -> type hint


@dataclass
class ToolMeta:
    name: str
    description: str
    schema: ToolSchema = field(default_factory=ToolSchema)
    destructive: bool = False
    permissions: List[str] = field(default_factory=list)


class Tool(ABC):
    """Abstract tool. Subclasses set ``meta`` and implement ``run``."""

    meta: ToolMeta = ToolMeta(name="tool", description="")

    @abstractmethod
    def run(self, args: Dict[str, Any], user_id: str = "cli") -> Dict[str, Any]:
        """Execute and return a structured dict (always includes ``ok``)."""

    # -- helpers -------------------------------------------------------------
    def validate(self, args: Dict[str, Any]) -> Optional[str]:
        """Return an error string if required args are missing, else None."""
        for key in self.meta.schema.required:
            if key not in args or args[key] in ("", None):
                return f"missing required argument: {key}"
        return None

    def describe(self) -> Dict[str, Any]:
        m = self.meta
        return {
            "name": m.name,
            "description": m.description,
            "destructive": m.destructive,
            "permissions": list(m.permissions),
            "schema": {"required": list(m.schema.required), "optional": dict(m.schema.optional)},
        }


class ToolRegistry:
    """Holds tools and runs them (with validation). Permission gating is the
    caller's responsibility (supervisor.run_tool checks security first)."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.meta.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list(self) -> List[str]:
        return sorted(self._tools)

    def describe_all(self) -> List[Dict[str, Any]]:
        return [t.describe() for t in self._tools.values()]

    def run(self, name: str, args: Dict[str, Any], user_id: str = "cli") -> Dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"ok": False, "error": f"unknown tool: {name}"}
        err = tool.validate(args)
        if err:
            return {"ok": False, "error": err}
        try:
            return tool.run(args, user_id=user_id)
        except Exception as exc:  # noqa: BLE001 — tools must not crash the OS
            return {"ok": False, "error": str(exc)}
