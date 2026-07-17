#!/usr/bin/env python3
"""
base.py — Standardized Tool Framework Base Classes for KAGE OS.
Provides BaseTool, ToolMetadata, PermissionLevel, and ToolResult.
Part of Phase 8 Tool Framework.
"""

import abc
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple

logger = logging.getLogger("kage.tools")


class PermissionLevel(Enum):
    SAFE = "safe"           # Auto-approve read/telemetry operations
    SENSITIVE = "sensitive"  # Requires explicit prompt approval
    CRITICAL = "critical"   # System modification / security critical


@dataclass
class ToolMetadata:
    """Metadata specification for standard tool definitions."""
    name: str
    description: str
    category: str
    version: str = "1.0.0"
    permission_level: PermissionLevel = PermissionLevel.SAFE
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    max_retries: int = 1


@dataclass
class ToolResult:
    """Structured result returned by tool execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    logs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "logs": self.logs,
        }


class BaseTool(abc.ABC):
    """Abstract Base Class for all KAGE OS system tools."""

    def __init__(self, metadata: ToolMetadata):
        self.metadata = metadata

    def validate_args(self, args: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate argument dictionary against parameters_schema required fields."""
        required = self.metadata.parameters_schema.get("required", [])
        for req_param in required:
            if req_param not in args or args[req_param] is None:
                return False, f"Missing required parameter '{req_param}'"
        return True, ""

    @abc.abstractmethod
    def run(self, args: Dict[str, Any]) -> Any:
        """Core execution logic for tool."""
        pass

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """Execute tool with input validation, timeout monitoring, and logging."""
        is_valid, err_msg = self.validate_args(args)
        if not is_valid:
            return ToolResult(success=False, error=err_msg)

        start_t = time.time()
        tool_logs = [f"Executing tool '{self.metadata.name}' with args: {args}"]

        try:
            output = self.run(args)
            duration_ms = (time.time() - start_t) * 1000
            tool_logs.append(f"Execution completed in {duration_ms:.2f}ms")
            return ToolResult(success=True, output=output, duration_ms=duration_ms, logs=tool_logs)
        except Exception as e:
            duration_ms = (time.time() - start_t) * 1000
            tool_logs.append(f"Execution failed: {e}")
            logger.error(f"Tool '{self.metadata.name}' error: {e}")
            return ToolResult(success=False, error=str(e), duration_ms=duration_ms, logs=tool_logs)
