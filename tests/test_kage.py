#!/usr/bin/env python3
"""
Unit and Integration Tests for KAGE OS v2.1 & Phase 3 REPL.
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

    def test_provider_models_dictionary(self):
        self.assertIn("gemini", brain.PROVIDER_MODELS)
        self.assertIn("groq", brain.PROVIDER_MODELS)
        self.assertIn("openrouter", brain.PROVIDER_MODELS)
        self.assertIn("ollama", brain.PROVIDER_MODELS)
        self.assertIn("llama-3.3-70b-versatile", brain.PROVIDER_MODELS["groq"])


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
        self.assertTrue(permissions.require_approval("obsidian.read"))
        self.assertTrue(permissions.require_approval("browser.search"))

    def test_auto_approve_flag(self):
        self.assertTrue(permissions.require_approval("obsidian.write", auto_approve=True))


class TestPhase3ReplConfig(unittest.TestCase):
    def test_mask_secret(self):
        masked = kage_cli.mask_secret("api_key", "AQ.Ab8RN6JL_eB0nDt_12345")
        self.assertTrue(masked.startswith("AQ.A"))
        self.assertTrue(masked.endswith("2345"))
        self.assertIn("***", masked)

    def test_dynamic_config_setter_and_getter(self):
        set_success = kage_cli.set_config_key("llm.test_field", "unit_test_value")
        self.assertTrue(set_success)
        val = kage_cli.get_config_value("llm.test_field")
        self.assertEqual(val, "unit_test_value")


if __name__ == "__main__":
    unittest.main()
