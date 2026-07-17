#!/usr/bin/env python3
"""
Unit and Integration Tests for KAGE OS Phases 2 & 3.
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
from core.integrations import (
    ProviderRegistry,
    AbstractBaseIntegration,
    HealthStatus,
    RetryEngine,
    RateLimiter,
    PluginLoader,
)
from core.integrations.providers import (
    GeminiProvider,
    GroqProvider,
    OpenRouterProvider,
    OllamaProvider,
    ObsidianProvider,
    WhatsAppProvider,
    TelegramProvider,
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

    def test_truncate(self):
        text = "a" * 300
        truncated = helpers.truncate(text, 50)
        self.assertEqual(len(truncated), 53)
        self.assertTrue(truncated.endswith("..."))


class TestIntegrationsArchitecture(unittest.TestCase):
    def test_provider_registry_lookup(self):
        registered = ProviderRegistry.list_registered_providers()
        self.assertIn("gemini", registered)
        self.assertIn("groq", registered)
        self.assertIn("obsidian", registered)
        self.assertIn("telegram", registered)

    def test_provider_instantiation_and_health(self):
        inst = ProviderRegistry.get_instance("obsidian", {"url": "http://localhost:27123"})
        self.assertIsNotNone(inst)
        self.assertIsInstance(inst, AbstractBaseIntegration)
        health = inst.health_check()
        self.assertIsInstance(health, HealthStatus)

    def test_retry_engine_failure_recovery(self):
        attempts = 0

        def failing_func():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ValueError("Temporary glitch")
            return "recovered"

        retry_engine = RetryEngine(max_retries=3, initial_delay=0.01, backoff_factor=1.1)
        res = retry_engine.execute_with_retry(failing_func, retryable_exceptions=(ValueError,))
        self.assertEqual(res, "recovered")
        self.assertEqual(attempts, 2)

    def test_rate_limiter_acquisition(self):
        limiter = RateLimiter(max_calls=10, period_seconds=1.0)
        acquired = limiter.acquire()
        self.assertTrue(acquired)


class TestWorkflowEngine(unittest.TestCase):
    def setUp(self):
        memory.init_db()
        self.supervisor = kage.Kage()
        self.supervisor.init_context()
        self.engine = workflows.WorkflowEngine(supervisor=self.supervisor)

    def test_workflow_registration_and_execution(self):
        steps = [
            {"target": "openhands", "action": "run_python", "params": {"code": "print('workflow_step_1')"}},
            {"target": "openhands", "action": "run_python", "params": {"code": "print('workflow_step_2')"}}
        ]
        wf_id = self.engine.register_workflow("test_pipeline", steps)
        self.assertIsInstance(wf_id, int)

        exec_res = self.engine.run_workflow(wf_id)
        self.assertEqual(exec_res["status"], "completed")
        self.assertEqual(len(exec_res["step_results"]), 2)


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


class TestCoreBrain(unittest.TestCase):
    def test_extract_action_json(self):
        raw = 'Here is the action:\n```json\n{"action": "openhands", "task": {"action": "execute_cmd", "command": "ls -la"}}\n```'
        parsed = brain.extract_action_json(raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["action"], "openhands")


if __name__ == "__main__":
    unittest.main()
