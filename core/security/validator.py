#!/usr/bin/env python3
"""
validator.py — Path Validation & Input Sanitization Framework for KAGE OS.
Prevents directory traversal attacks, restricts workspace root escape, and sanitizes input arguments.
Part of Phase 9 Hardened Security Framework.
"""

import os
import re
from pathlib import Path
from typing import Union, Optional


class SafePathValidator:
    """Validates filesystem paths against unauthorized directory traversal attacks."""

    def __init__(self, allowed_roots: Optional[list] = None):
        self.allowed_roots = [
            Path(r).resolve() for r in (allowed_roots or [
                Path.cwd(),
                Path.home() / ".kage",
                Path.home() / "kage-os",
                "/home/user/KAGE-CLI"
            ])
            if Path(r).exists()
        ]

    def validate_path(self, target_path: Union[str, Path]) -> Path:
        """Resolve path and ensure it remains within authorized filesystem boundaries."""
        resolved = Path(target_path).resolve()

        # Check path traversal attempts (../)
        is_allowed = any(
            str(resolved).startswith(str(root))
            for root in self.allowed_roots
        )

        if not is_allowed:
            raise PermissionError(
                f"Security Violation: Target path '{resolved}' outside authorized workspace roots ({[str(r) for r in self.allowed_roots]})"
            )

        return resolved


class InputSanitizer:
    """Sanitizes raw prompt inputs and command parameters."""

    @staticmethod
    def sanitize_command_args(args: list) -> list:
        """Strip dangerous control characters from argument tokens."""
        sanitized = []
        for arg in args:
            str_arg = str(arg)
            # Remove NULL bytes and non-printable control characters
            clean_arg = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str_arg)
            sanitized.append(clean_arg)
        return sanitized
