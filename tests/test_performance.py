#!/usr/bin/env python3
"""
Unit tests for Performance Engine (core/performance/).
"""

import time
import unittest
from core.performance import ResponseCache, AsyncEngine


class TestPerformanceEngine(unittest.TestCase):
    def setUp(self):
        self.cache = ResponseCache(default_ttl_seconds=2)

    def test_response_cache_set_get(self):
        key = {"prompt": "What is AI?", "model": "gemini-2.5-flash"}
        self.cache.set(key, "Artificial Intelligence definition")

        val = self.cache.get(key)
        self.assertEqual(val, "Artificial Intelligence definition")

    def test_response_cache_expiration(self):
        key = {"prompt": "Short lived"}
        self.cache.set(key, "temp_data", ttl_seconds=-1)
        val = self.cache.get(key)
        self.assertIsNone(val)

    def test_async_engine_execution(self):
        def add(a, b):
            return a + b

        res = AsyncEngine.run_coroutine(AsyncEngine.run_in_executor(add, 10, 20))
        self.assertEqual(res, 30)


if __name__ == "__main__":
    unittest.main()
