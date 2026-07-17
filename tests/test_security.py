#!/usr/bin/env python3
"""
Unit tests for Security Framework (core/security/).
"""

import unittest
from core.security import (
    SafePathValidator,
    InputSanitizer,
    SecretRedactor,
    SecurityManager,
)


class TestSecurityFramework(unittest.TestCase):
    def test_safe_path_validator_allowed(self):
        validator = SafePathValidator(allowed_roots=["/home/user/KAGE-CLI"])
        valid = validator.validate_path("/home/user/KAGE-CLI/README.md")
        self.assertTrue(str(valid).endswith("README.md"))

    def test_safe_path_validator_rejected(self):
        validator = SafePathValidator(allowed_roots=["/home/user/KAGE-CLI"])
        with self.assertRaises(PermissionError):
            validator.validate_path("/etc/passwd")

    def test_input_sanitizer(self):
        clean_args = InputSanitizer.sanitize_command_args(["ls\x00", "hello\x1fworld"])
        self.assertEqual(clean_args, ["ls", "helloworld"])

    def test_secret_redactor(self):
        token_str = "Key AQ.Ab8RN6JL_sample_key_1234567890 active"
        redacted = SecretRedactor.redact_text(token_str)
        self.assertNotIn("sample_key", redacted)
        self.assertIn("***[REDACTED]***", redacted)

    def test_security_manager_policies(self):
        mgr = SecurityManager()
        self.assertTrue(mgr.is_safe_action("system.health"))
        self.assertFalse(mgr.is_safe_action("openhands.execute_cmd"))


if __name__ == "__main__":
    unittest.main()
