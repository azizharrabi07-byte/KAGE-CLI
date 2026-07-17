#!/usr/bin/env python3
"""
Unit tests for Prompt Engine (core/prompts/).
"""

import unittest
from core.prompts import (
    PromptTemplate,
    PromptVersionRegistry,
    PromptCompressor,
    ContextBuilder,
)


class TestPromptEngine(unittest.TestCase):
    def test_prompt_template_rendering(self):
        tpl = PromptTemplate("greeting", "1.0", "Hello {{user}}, system {{sys}} active")
        res = tpl.render(user="Alex", sys="KAGE")
        self.assertEqual(res, "Hello Alex, system KAGE active")

    def test_prompt_version_registry(self):
        tpl = PromptVersionRegistry.get("system", "latest")
        self.assertIsNotNone(tpl)
        self.assertIn("Kage", tpl.template_text)

    def test_context_builder(self):
        builder = ContextBuilder()
        system_inst = builder.build_system_instruction("usr_123", extra_instructions="Strict concise format")
        self.assertIn("Kage", system_inst)
        self.assertIn("Strict concise format", system_inst)


if __name__ == "__main__":
    unittest.main()
