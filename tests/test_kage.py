#!/usr/bin/env python3
"""
Unit and Integration Tests for KAGE OS User Memory & Integrations.
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
from core import brain, memory, permissions, scheduler, user_memory
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


class TestUserMemory(unittest.TestCase):
    def test_user_memory_storage_and_prompt(self):
        uid = "test_user_42"
        user_memory.set_user_name(uid, "Jordan")
        user_memory.add_user_fact(uid, "Loves open-source AI")

        u_mem = user_memory.get_user_memory(uid)
        self.assertEqual(u_mem["name"], "Jordan")
        self.assertIn("Loves open-source AI", u_mem["facts"])

        prompt_str = user_memory.format_user_memory_prompt(uid)
        self.assertIn("Jordan", prompt_str)
        self.assertIn("Loves open-source AI", prompt_str)


class TestCoreBrain(unittest.TestCase):
    def test_extract_action_json(self):
        raw = 'Here is the action:\n```json\n{"action": "openhands", "task": {"action": "execute_cmd", "command": "ls -la"}}\n```'
        parsed = brain.extract_action_json(raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["action"], "openhands")
        self.assertEqual(parsed["task"]["command"], "ls -la")

    def test_provider_models_dictionary(self):
        self.assertIn("gemini", brain.PROVIDER_MODELS)
        self.assertIn("groq", brain.PROVIDER_MODELS)
        self.assertIn("openrouter", brain.PROVIDER_MODELS)
        self.assertIn("ollama", brain.PROVIDER_MODELS)


class TestCoreMemory(unittest.TestCase):
    def setUp(self):
        memory.init_db()

    def test_trace_logging(self):
        trace_id = memory.log_trace("telegram", {"action": "test"}, {"status": "ok"}, duration_ms=10.5)
        self.assertIsInstance(trace_id, int)
        trace = memory.get_trace_by_id(trace_id)
        self.assertIsNotNone(trace)
        self.assertEqual(trace["agent"], "telegram")


class TestCorePermissions(unittest.TestCase):
    def test_safe_actions(self):
        self.assertTrue(permissions.require_approval("system.health"))
        self.assertTrue(permissions.require_approval("telegram.status"))

    def test_auto_approve_flag(self):
        self.assertTrue(permissions.require_approval("telegram.send", auto_approve=True))


class TestTelegramAgent(unittest.TestCase):
    def setUp(self):
        self.supervisor = kage.Kage()
        self.supervisor.init_context()

    def test_telegram_agent_wake_status(self):
        res = self.supervisor.wake("telegram", {"action": "status"})
        self.assertEqual(res["status"], "done")
        out = res.get("output", {})
        self.assertEqual(out.get("status"), "connected")
        self.assertEqual(out.get("username"), "@Mini_kage_bot")


if __name__ == "__main__":
    unittest.main()
