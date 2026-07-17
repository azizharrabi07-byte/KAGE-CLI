#!/usr/bin/env python3
"""
Unit and Integration Tests for KAGE OS Phases 6 & 7.
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
from core.cli import (
    TableFormatter,
    OutputFormatter,
    CLICompleter,
    ExecutionFlags,
    CommandRunner,
)
from core.memory import (
    MemoryItem,
    MemoryType,
    MemoryStore,
    SemanticIndex,
    MemoryManager,
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


class TestPhase6CLI(unittest.TestCase):
    def test_table_formatter(self):
        headers = ["ID", "Name", "Role"]
        rows = [["1", "Alex", "Admin"], ["2", "Jordan", "User"]]
        tbl = TableFormatter.render_table(headers, rows, title="Users")
        self.assertIn("Alex", tbl)
        self.assertIn("Admin", tbl)

    def test_output_formatter_json_and_yaml(self):
        payload = {"status": "ok", "count": 42}
        json_out = OutputFormatter.format_output(payload, "json")
        self.assertIn('"count": 42', json_out)

        yaml_out = OutputFormatter.format_output(payload, "yaml")
        self.assertIn("status: ok", yaml_out)

    def test_cli_completer(self):
        completer = CLICompleter()
        match1 = completer.complete("/con", 0)
        self.assertIn("/config", match1)

    def test_command_runner_dry_run(self):
        runner = CommandRunner(flags=ExecutionFlags(dry_run=True, format_output="json"))
        out = runner.run("status", {})
        self.assertIn("dry_run", out)


class TestPhase7MemoryEngine(unittest.TestCase):
    def setUp(self):
        self.mgr = MemoryManager()

    def test_memory_importance_and_item(self):
        item = self.mgr.add_memory(
            content="User loves Python and Termux",
            user_id="unit_user",
            memory_type=MemoryType.KNOWLEDGE,
            importance=8.5
        )
        self.assertEqual(item.importance, 8.5)
        self.assertEqual(item.user_id, "unit_user")

    def test_semantic_vector_search(self):
        self.mgr.add_memory("User primary language is Rust", user_id="sec_user", importance=9.0)
        self.mgr.add_memory("User enjoys playing chess", user_id="sec_user", importance=5.0)

        results = self.mgr.search_memories("programming language Rust", user_id="sec_user")
        self.assertTrue(len(results) > 0)
        self.assertIn("Rust", results[0]["content"])

    def test_memory_ttl_expiration(self):
        item = MemoryItem(
            memory_type=MemoryType.WORKING,
            content="Temporary buffer",
            ttl_seconds=-10  # Already expired
        )
        self.assertTrue(item.is_expired())


if __name__ == "__main__":
    unittest.main()
