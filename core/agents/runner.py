#!/usr/bin/env python3
"""
runner.py — Agent Execution & Parallel Worker Pool Manager for KAGE OS.
Supports concurrent multi-agent task dispatch, cancellation propagation, and metric collection.
Part of Phase 5 Agent Framework.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Tuple
from .base import BaseAgent

logger = logging.getLogger("kage.agent_runner")


class AgentRunner:
    """Orchestrates parallel execution and thread pool dispatch across Kage agents."""

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="KageAgentWorker")

    def run_agent_task(self, agent: BaseAgent, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task on a single agent using safe wake wrapper."""
        logger.info(f"Runner dispatching task to agent '{agent.name}'")
        return agent.safe_wake(task_data)

    def run_parallel(self, tasks: List[Tuple[BaseAgent, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Run multiple (agent, task_data) pairs concurrently in parallel thread workers."""
        futures = {}
        for agent, task in tasks:
            fut = self.executor.submit(agent.safe_wake, task)
            futures[fut] = agent.name

        results = []
        for fut in as_completed(futures):
            ag_name = futures[fut]
            try:
                res = fut.result()
                results.append({"agent": ag_name, "result": res})
            except Exception as e:
                logger.error(f"Parallel task failed for agent '{ag_name}': {e}")
                results.append({"agent": ag_name, "result": {"status": "error", "error": str(e)}})

        return results

    def shutdown(self):
        """Shutdown executor thread pool."""
        self.executor.shutdown(wait=False)
