#!/usr/bin/env python3
"""
Unit and Integration Tests for KAGE OS Phases 8 & 9.
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
from core.tools import (
    BaseTool,
    ToolMetadata,
    PermissionLevel,
    ToolResult,
    ToolRegistry,
)
from core.tools.implementations import (
    BashTool,
    PythonTool,
    FileTool,
    WebTool,
    MemoryTool,
)
from core.security import (
    SafePathValidator,
    InputSanitizer,
    SecretRedactor,
    SecurityManager,
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


class TestPhase8ToolFramework(unittest.TestCase):
    def test_tool_registry_lookup(self):
        tool = ToolRegistry.get_tool("bash_execute")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.metadata.name, "bash_execute")

    def test_bash_tool_execution(self):
        res = ToolRegistry.execute_tool("bash_execute", {"command": "echo 'hello_tool'"})
        self.assertTrue(res.success)
        self.assertEqual(res.output.get("stdout"), "hello_tool")

    def test_file_tool_path_traversal_blocking(self):
        file_tool = FileTool(root_dir="/home/user/KAGE-CLI")
        res = file_tool.execute({"action": "read", "path": "../../../etc/passwd"})
        self.assertFalse(res.success)
        self.assertIn("Access denied", res.error)

    def test_python_tool_evaluation(self):
        res = ToolRegistry.execute_tool("python_eval", {"code": "print(10 + 32)"})
        self.assertTrue(res.success)
        self.assertEqual(res.output.get("stdout"), "42")


class TestPhase9SecurityFramework(unittest.TestCase):
    def test_path_validator_authorized(self):
        validator = SafePathValidator(allowed_roots=["/home/user/KAGE-CLI"])
        valid_path = validator.validate_path("/home/user/KAGE-CLI/README.md")
        self.assertTrue(str(valid_path).endswith("README.md"))

    def test_path_validator_traversal_rejection(self):
        validator = SafePathValidator(allowed_roots=["/home/user/KAGE-CLI"])
        with self.assertRaises(PermissionError):
            validator.validate_path("/etc/shadow")

    def test_secret_redactor_text(self):
        raw_log = "Error using key AQ.Ab8RN6JL_sample_test_key_1234567890 on model"
        redacted = SecretRedactor.redact_text(raw_log)
        self.assertNotIn("sample_test_key_1234567890", redacted)
        self.assertIn("***[REDACTED]***", redacted)

    def test_secret_redactor_dict_structure(self):
        payload = {
            "user": "alex",
            "api_key": "4224414d3d95d207e1058d16f30424c9",
            "nested": {"token": "8819096503:AAEqOGM_sample_token_1234567890"}
        }
        redacted = SecretRedactor.redact_structure(payload)
        self.assertNotIn("4224414d3d95d207e1058d16f30424c9", json.dumps(redacted))
        self.assertIn("***[REDACTED]***", redacted["api_key"])

    def test_security_manager_safe_whitelist(self):
        sec_mgr = SecurityManager()
        self.assertTrue(sec_mgr.is_safe_action("system.health"))
        self.assertTrue(sec_mgr.is_safe_action("browser.search"))


if __name__ == "__main__":
    unittest.main()
