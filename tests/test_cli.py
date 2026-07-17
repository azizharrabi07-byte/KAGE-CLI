#!/usr/bin/env python3
"""
Unit tests for CLI Engine (core/cli/).
"""

import unittest
from core.cli import (
    TableFormatter,
    OutputFormatter,
    CLICompleter,
    ExecutionFlags,
    CommandRunner,
)


class TestCLIEngine(unittest.TestCase):
    def test_table_formatter(self):
        headers = ["Col1", "Col2"]
        rows = [["Val1", "Val2"], ["A", "B"]]
        rendered = TableFormatter.render_table(headers, rows, title="Test Table")
        self.assertIn("Col1", rendered)
        self.assertIn("Val1", rendered)
        self.assertIn("TEST TABLE", rendered)

    def test_output_formatter_json_yaml(self):
        data = {"key": "value", "items": [1, 2, 3]}
        j_out = OutputFormatter.format_output(data, "json")
        self.assertIn('"key": "value"', j_out)

        y_out = OutputFormatter.format_output(data, "yaml")
        self.assertIn("key: value", y_out)

    def test_cli_completer(self):
        completer = CLICompleter(["/help", "/config list", "/status"])
        m1 = completer.complete("/con", 0)
        self.assertEqual(m1, "/config list")

    def test_command_runner_dry_run(self):
        runner = CommandRunner(flags=ExecutionFlags(dry_run=True, format_output="json"))
        out = runner.run("chat", {"message": "hello"})
        self.assertIn("dry_run", out)


if __name__ == "__main__":
    unittest.main()
