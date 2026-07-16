#!/usr/bin/env python3
"""
Unit and Integration Tests for KAGE OS.
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
from core import brain, memory, permissions, scheduler
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

    def test_truncate(self):
        text = "a" * 300
        truncated = helpers.truncate(text, 50)
        self.assertEqual(len(truncated), 53)
        self.assertTrue(truncated.endswith("..."))


class TestCoreBrain(unittest.TestCase):
    def test_extract_action_json(self):
        raw = 'Here is the action:\n```json\n{"action": "system", "task": {"action": "health"}}\n```'
        parsed = brain.extract_action_json(raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["action"], "system")

    def test_extract_nested_feature_action(self):
        raw = 'I will run: {"action": "browser", "task": {"action": "search", "query": "Python"}}'
        parsed = brain.extract_action_json(raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["action"], "browser")

    def test_call_llm_gemini_integration(self):
        res = brain.call_llm([{"role": "user", "content": "Respond short: active"}])
        self.assertIn("content", res)
        self.assertIsNotNone(res["content"])


class TestCoreMemory(unittest.TestCase):
    def setUp(self):
        memory.init_db()

    def test_trace_logging(self):
        trace_id = memory.log_trace("system", {"action": "test"}, {"status": "ok"}, duration_ms=10.5)
        self.assertIsInstance(trace_id, int)
        trace = memory.get_trace_by_id(trace_id)
        self.assertIsNotNone(trace)
        self.assertEqual(trace["agent"], "system")

    def test_schedule_crud(self):
        job_id = memory.add_schedule("0 9 * * *", "system", {"action": "health"})
        self.assertIsInstance(job_id, int)
        schedules = memory.get_schedules()
        self.assertTrue(any(s["id"] == job_id for s in schedules))
        memory.delete_schedule(job_id)
        schedules_after = memory.get_schedules()
        self.assertFalse(any(s["id"] == job_id for s in schedules_after))


class TestCorePermissions(unittest.TestCase):
    def test_safe_actions(self):
        self.assertTrue(permissions.require_approval("system.health"))
        self.assertTrue(permissions.require_approval("browser.search"))
        self.assertTrue(permissions.require_approval("mcp.list_tools"))

    def test_auto_approve_flag(self):
        self.assertTrue(permissions.require_approval("openhands.execute_cmd", auto_approve=True))


class TestBuiltInFeatures(unittest.TestCase):
    def setUp(self):
        self.supervisor = kage.Kage()
        self.supervisor.init_context()

    def test_browser_feature_context(self):
        self.assertTrue(hasattr(self.supervisor.context, "browser"))
        results = self.supervisor.context.browser.search("Python")
        self.assertIsInstance(results, list)

    def test_openhands_feature_context(self):
        self.assertTrue(hasattr(self.supervisor.context, "openhands"))
        res = self.supervisor.context.openhands.execute_cmd("echo 'hello'", require_approval=False)
        self.assertEqual(res["stdout"], "hello")

    def test_mcp_feature_context(self):
        self.assertTrue(hasattr(self.supervisor.context, "mcp"))
        servers = self.supervisor.context.mcp.list_servers()
        self.assertIsInstance(servers, list)

    def test_crew_feature_context(self):
        self.assertTrue(hasattr(self.supervisor.context, "crew"))
        templates = self.supervisor.context.crew.list_templates()
        self.assertIsInstance(templates, list)


if __name__ == "__main__":
    unittest.main()
