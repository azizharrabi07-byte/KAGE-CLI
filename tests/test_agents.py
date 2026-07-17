#!/usr/bin/env python3
"""
Unit tests for Agent Framework (core/agents/).
"""

import unittest
from core.agents import (
    BaseAgent,
    AgentMetrics,
    TaskAgent,
    ChatAgent,
    ToolAgent,
    PlanningAgent,
    MemoryAgent,
    ExecutionAgent,
    BackgroundAgent,
    AgentRunner,
)


class TestAgentFramework(unittest.TestCase):
    def test_agent_metrics(self):
        m = AgentMetrics()
        m.record_success(50.0)
        m.record_failure(150.0)
        d = m.to_dict()
        self.assertEqual(d["invocations"], 2)
        self.assertEqual(d["successes"], 1)
        self.assertEqual(d["failures"], 1)
        self.assertEqual(d["avg_latency_ms"], 100.0)

    def test_task_agent_wake(self):
        agent = TaskAgent("task_worker")
        res = agent.safe_wake({"action": "sample_task"})
        self.assertEqual(res["status"], "done")
        self.assertEqual(agent.metrics.successes, 1)

    def test_tool_agent_execution(self):
        agent = ToolAgent("tool_worker")
        agent.register_tool("echo_tool", lambda text: f"echo_{text}")
        res = agent.safe_wake({"tool": "echo_tool", "args": {"text": "hello"}})
        self.assertEqual(res["status"], "done")
        self.assertEqual(res["output"], "echo_hello")

    def test_agent_runner_parallel(self):
        ag1 = TaskAgent("ag1")
        ag2 = TaskAgent("ag2")
        runner = AgentRunner(max_workers=2)
        results = runner.run_parallel([
            (ag1, {"action": "a1"}),
            (ag2, {"action": "a2"}),
        ])
        runner.shutdown()
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
