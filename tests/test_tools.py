#!/usr/bin/env python3
"""
Unit tests for Tool Framework (core/tools/).
"""

import unittest
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
)


class TestToolFramework(unittest.TestCase):
    def test_tool_registry_registration(self):
        tool = ToolRegistry.get_tool("bash_execute")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.metadata.category, "execution")

    def test_bash_tool_execution(self):
        bash_tool = BashTool()
        res = bash_tool.execute({"command": "echo 'test_tool'"})
        self.assertTrue(res.success)
        self.assertEqual(res.output.get("stdout"), "test_tool")

    def test_python_tool_evaluation(self):
        python_tool = PythonTool()
        res = python_tool.execute({"code": "print(5 * 5)"})
        self.assertTrue(res.success)
        self.assertEqual(res.output.get("stdout"), "25")

    def test_file_tool_traversal_blocking(self):
        file_tool = FileTool(root_dir="/home/user/KAGE-CLI")
        res = file_tool.execute({"action": "read", "path": "../../../etc/passwd"})
        self.assertFalse(res.success)
        self.assertIn("Access denied", res.error)


if __name__ == "__main__":
    unittest.main()
