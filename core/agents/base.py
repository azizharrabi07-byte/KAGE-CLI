#!/usr/bin/env python3
"""
base.py — Abstract Base Agent & Metrics Architecture for KAGE OS.
Provides BaseAgent, AgentMetrics, and shared capabilities (planning, reflection, reasoning, metrics, tools).
Part of Phase 5 Agent Framework.
"""

import abc
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

from core.prompts import (
    ContextBuilder,
    PLANNER_PROMPT,
    REASONING_PROMPT,
    REFLECTION_PROMPT,
    PromptCompressor,
)

logger = logging.getLogger("kage.agents")


@dataclass
class AgentMetrics:
    """Metrics collector tracking agent execution statistics."""
    invocations: int = 0
    successes: int = 0
    failures: int = 0
    total_duration_ms: float = 0.0

    def record_success(self, duration_ms: float):
        self.invocations += 1
        self.successes += 1
        self.total_duration_ms += duration_ms

    def record_failure(self, duration_ms: float):
        self.invocations += 1
        self.failures += 1
        self.total_duration_ms += duration_ms

    def to_dict(self) -> Dict[str, Any]:
        avg_ms = (self.total_duration_ms / self.invocations) if self.invocations > 0 else 0.0
        return {
            "invocations": self.invocations,
            "successes": self.successes,
            "failures": self.failures,
            "avg_latency_ms": round(avg_ms, 2),
            "total_latency_ms": round(self.total_duration_ms, 2),
        }


class BaseAgent(abc.ABC):
    """Abstract Base Class for all KAGE OS agents."""

    def __init__(self, name: str, context: Optional[Any] = None, description: str = ""):
        self.name = name
        self.context = context
        self.description = description
        self.alive = False
        self.is_cancelled = False
        self.metrics = AgentMetrics()
        self.tools: Dict[str, Callable] = {}
        self.context_builder = ContextBuilder()

    def register_tool(self, name: str, tool_fn: Callable):
        """Register a tool callable on this agent instance."""
        self.tools[name] = tool_fn

    def cancel(self):
        """Cancel active agent operations."""
        self.is_cancelled = True
        logger.info(f"Agent '{self.name}' requested cancellation")

    def plan(self, goal: str, constraints: str = "") -> Dict[str, Any]:
        """Construct a step-by-step action plan for achieving a goal."""
        prompt = PLANNER_PROMPT.render(goal=goal, constraints=constraints)
        if self.context and hasattr(self.context, "brain"):
            res = self.context.brain.process_command("chat", {"message": prompt})
            return {"status": "done", "plan_raw": res.get("response", "")}
        return {"status": "done", "plan_raw": f"Plan for {goal}"}

    def reason(self, query: str, observation: str = "") -> Dict[str, Any]:
        """Perform step-by-step chain-of-thought analysis."""
        prompt = REASONING_PROMPT.render(query=query, observation=observation)
        if self.context and hasattr(self.context, "brain"):
            res = self.context.brain.process_command("chat", {"message": prompt})
            return {"status": "done", "reasoning": res.get("response", "")}
        return {"status": "done", "reasoning": f"Reasoning analysis for {query}"}

    def reflect(self, goal: str, output: Any) -> Dict[str, Any]:
        """Critique and validate execution output against goal."""
        out_str = json.dumps(output) if isinstance(output, (dict, list)) else str(output)
        prompt = REFLECTION_PROMPT.render(goal=goal, result=out_str)
        if self.context and hasattr(self.context, "brain"):
            res = self.context.brain.process_command("chat", {"message": prompt})
            return {"status": "done", "reflection": res.get("response", "")}
        return {"status": "done", "reflection": f"Reflection on output for {goal}"}

    def compress_context(self, text: str, max_chars: int = 3000) -> str:
        """Prune context budget for model input."""
        return PromptCompressor.compress(text, max_chars=max_chars)

    @abc.abstractmethod
    def wake(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Wake up lifecycle hook."""
        pass

    @abc.abstractmethod
    def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Primary execution method."""
        pass

    def sleep(self):
        """Cleanup lifecycle hook."""
        self.alive = False

    def safe_wake(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Safely execute wake wrapper tracking execution metrics."""
        self.alive = True
        self.is_cancelled = False
        start_t = time.time()

        try:
            result = self.wake(task_data)
            duration_ms = (time.time() - start_t) * 1000
            if result.get("status") == "error":
                self.metrics.record_failure(duration_ms)
            else:
                self.metrics.record_success(duration_ms)
            return result
        except Exception as e:
            duration_ms = (time.time() - start_t) * 1000
            self.metrics.record_failure(duration_ms)
            logger.error(f"Agent '{self.name}' exception: {e}")
            return {"status": "error", "agent": self.name, "output": str(e)}
        finally:
            self.sleep()
