#!/usr/bin/env python3
"""
Unit tests for Memory Engine (core/memory/).
"""

import unittest
from core.memory import (
    MemoryItem,
    MemoryType,
    MemoryStore,
    SemanticIndex,
    MemoryManager,
)
from core import user_memory


class TestMemoryEngine(unittest.TestCase):
    def setUp(self):
        self.mgr = MemoryManager()

    def test_memory_item_expiration(self):
        item = MemoryItem(memory_type=MemoryType.WORKING, content="Temporary", ttl_seconds=-5)
        self.assertTrue(item.is_expired())

    def test_memory_add_and_search(self):
        self.mgr.add_memory("User enjoys coding in Python", user_id="p1", importance=8.0)
        self.mgr.add_memory("User likes drinking green tea", user_id="p1", importance=4.0)

        res = self.mgr.search_memories("Python coding", user_id="p1")
        self.assertTrue(len(res) > 0)
        self.assertIn("Python", res[0]["content"])

    def test_user_memory_persistent_facts(self):
        user_memory.set_user_name("test_user_7", "Sam")
        user_memory.add_user_fact("test_user_7", "Developer on Termux")

        prompt_context = user_memory.format_user_memory_prompt("test_user_7")
        self.assertIn("Sam", prompt_context)
        self.assertIn("Termux", prompt_context)


if __name__ == "__main__":
    unittest.main()
