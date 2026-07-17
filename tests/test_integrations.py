#!/usr/bin/env python3
"""
Unit tests for Integrations Architecture (core/integrations/).
"""

import unittest
from core.integrations import (
    ProviderRegistry,
    AbstractBaseIntegration,
    HealthStatus,
    RetryEngine,
    RateLimiter,
)
from core.integrations.providers import (
    GeminiProvider,
    GroqProvider,
    ObsidianProvider,
    WhatsAppProvider,
    TelegramProvider,
)


class TestIntegrationsFramework(unittest.TestCase):
    def test_provider_registry_list(self):
        providers = ProviderRegistry.list_registered_providers()
        self.assertIn("gemini", providers)
        self.assertIn("groq", providers)
        self.assertIn("obsidian", providers)
        self.assertIn("telegram", providers)

    def test_provider_instantiation(self):
        inst = ProviderRegistry.get_instance("obsidian", {"url": "http://localhost:27123"})
        self.assertIsNotNone(inst)
        self.assertIsInstance(inst, AbstractBaseIntegration)

    def test_retry_engine(self):
        attempts = 0

        def flaky():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise TimeoutError("Network timeout")
            return "ok"

        engine = RetryEngine(max_retries=3, initial_delay=0.01)
        res = engine.execute_with_retry(flaky, retryable_exceptions=(TimeoutError,))
        self.assertEqual(res, "ok")
        self.assertEqual(attempts, 2)


if __name__ == "__main__":
    unittest.main()
