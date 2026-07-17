#!/usr/bin/env python3
"""
types.py — Concrete Agent Class Hierarchy for KAGE OS.
Implements TaskAgent, ChatAgent, ToolAgent, PlanningAgent, MemoryAgent, ExecutionAgent, and BackgroundAgent.
Part of Phase 5 Agent Framework.
"""

import time
from typing import Dict, List, Optional, Any
from .base import BaseAgent


class TaskAgent(BaseAgent):
    """Agent specialized for executing domain-specific task schemas."""

    def wake(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(task_data)

    def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        action = task_data.get("action", "default")
        return {"status": "done", "agent": self.name, "output": f"Executed task action '{action}'"}


class ChatAgent(BaseAgent):
    """Agent specialized for natural language chat interaction and context routing."""

    def wake(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(task_data)

    def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        message = task_data.get("message", "")
        user_id = task_data.get("user_id", "default")
        if self.context and hasattr(self.context, "brain"):
            return self.context.brain._handle_chat(message, user_id=user_id)
        return {"status": "done", "response": f"Echo: {message}"}


class ToolAgent(BaseAgent):
    """Agent dedicated to external API and tool invocation wrappers."""

    def wake(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(task_data)

    def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = task_data.get("tool", "")
        args = task_data.get("args", {})
        if tool_name in self.tools:
            res = self.tools[tool_name](**args)
            return {"status": "done", "output": res}
        return {"status": "error", "output": f"Tool '{tool_name}' not registered on agent '{self.name}'"}


class PlanningAgent(BaseAgent):
    """Agent dedicated to multi-step plan construction and blueprint validation."""

    def wake(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(task_data)

    def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        goal = task_data.get("goal", "")
        return self.plan(goal=goal, constraints=task_data.get("constraints", ""))


class MemoryAgent(BaseAgent):
    """Agent managing persistent per-user memory extraction and storage."""

    def wake(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(task_data)

    def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        from core import user_memory
        user_id = task_data.get("user_id", "default")
        action = task_data.get("action", "get")

        if action == "remember":
            fact = task_data.get("fact")
            name = task_data.get("name")
            if name:
                user_memory.set_user_name(user_id, name)
            if fact:
                user_memory.add_user_fact(user_id, fact)
            return {"status": "done", "output": f"Saved memory for user '{user_id}'"}
        else:
            mem = user_memory.get_user_memory(user_id)
            return {"status": "done", "output": mem}


class ExecutionAgent(BaseAgent):
    """Agent executing sandboxed terminal commands and workspace code synthesis."""

    def wake(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(task_data)

    def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.context and hasattr(self.context, "openhands"):
            cmd = task_data.get("command")
            code = task_data.get("code")
            if cmd:
                return {"status": "done", "output": self.context.openhands.execute_cmd(cmd)}
            elif code:
                return {"status": "done", "output": self.context.openhands.run_python(code)}
        return {"status": "error", "output": "Execution feature unavailable"}


class BackgroundAgent(BaseAgent):
    """Agent managing background long-polling workers and persistent service daemons."""

    def wake(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(task_data)

    def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "done", "output": f"Background service '{self.name}' active"}
