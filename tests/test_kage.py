#!/usr/bin/env python3
"""
Unit and Integration Tests for KAGE OS Phases 4 & 5.
Run with: python3 -m unittest discover -s tests
"""

import json
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills import helpers
from core import brain, memory, permissions, scheduler, user_memory, workflows
from core.prompts import (
    PromptTemplate,
    PromptVersionRegistry,
    PromptCompressor,
    ContextBuilder,
    SYSTEM_PROMPT,
    DEVELOPER_PROMPT,
    PLANNER_PROMPT,
    REASONING_PROMPT,
    REFLECTION_PROMPT,
)
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
import kage
import kage_cli


class TestSkillsHelpers(unittest.TestCase):
    def test_format_response(self):
        res = helpers.format_response("done", output="hello")
        self.assertEqual(res["status"], "done")
        self.assertEqual(res["output"], "hello")

    def test_parse_json_safe(self):
        valid = helpers.parse_json_safe('{"key": "value"}')
        self.assertEqual(valid, {"key": "value"})
        invalid = helpers.parse_json_safe('invalid json')
        self.assertIsNone(invalid)


class TestPhase4Prompts(unittest.TestCase):
    def test_prompt_template_rendering(self):
        tpl = PromptTemplate("custom", "v1.0", "Hello {{name}}, welcome to $system!")
        rendered = tpl.render(name="Alex", system="KAGE")
        self.assertEqual(rendered, "Hello Alex, welcome to KAGE!")

    def test_prompt_version_registry(self):
        tpl = PromptVersionRegistry.get("system", "v2.1")
        self.assertIsNotNone(tpl)
        self.assertIn("Kage", tpl.template_text)

    def test_prompt_compressor(self):
        large_text = "line\n" * 500
        compressed = PromptCompressor.compress(large_text, max_chars=100)
        self.assertLessEqual(len(compressed), 150)
        self.assertIn("Compressed", compressed)

    def test_context_builder(self):
        builder = ContextBuilder()
        system_inst = builder.build_system_instruction(user_id="test_usr", extra_instructions="Be fast")
        self.assertIn("Kage", system_inst)
        self.assertIn("Be fast", system_inst)


class TestPhase5AgentFramework(unittest.TestCase):
    def setUp(self):
        self.supervisor = kage.Kage()
        self.supervisor.init_context()

    def test_agent_metrics(self):
        metrics = AgentMetrics()
        metrics.record_success(100.0)
        metrics.record_failure(200.0)
        m_dict = metrics.to_dict()
        self.assertEqual(m_dict["invocations"], 2)
        self.assertEqual(m_dict["successes"], 1)
        self.assertEqual(m_dict["failures"], 1)
        self.assertEqual(m_dict["avg_latency_ms"], 150.0)

    def test_agent_types_hierarchy(self):
        task_ag = TaskAgent("task_test", self.supervisor.context)
        res = task_ag.safe_wake({"action": "run_test"})
        self.assertEqual(res["status"], "done")
        self.assertIn("run_test", res["output"])

        plan_ag = PlanningAgent("plan_test", self.supervisor.context)
        plan_res = plan_ag.safe_wake({"goal": "Deploy OS"})
        self.assertEqual(plan_res["status"], "done")

    def test_agent_runner_parallel_execution(self):
        ag1 = TaskAgent("ag1", self.supervisor.context)
        ag2 = TaskAgent("ag2", self.supervisor.context)

        runner = AgentRunner(max_workers=2)
        parallel_results = runner.run_parallel([
            (ag1, {"action": "action1"}),
            (ag2, {"action": "action2"}),
        ])
        runner.shutdown()

        self.assertEqual(len(parallel_results), 2)
        agent_names = [r["agent"] for r in parallel_results]
        self.assertIn("ag1", agent_names)
        self.assertIn("ag2", agent_names)


if __name__ == "__main__":
    unittest.main()
