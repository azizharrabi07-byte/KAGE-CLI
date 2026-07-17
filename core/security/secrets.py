#!/usr/bin/env python3
"""
secrets.py — Secret Management & Automated Token Redaction Engine for KAGE OS.
Automatically scans and redacts API keys, passwords, and tokens from traces, logs, and outputs.
Part of Phase 9 Hardened Security Framework.
"""

import json
import re
from typing import Any, Dict, List, Union

# Regex patterns for detecting sensitive tokens
SECRET_PATTERNS = [
    re.compile(r"AQ\.[A-Za-z0-9_\-]{30,}", re.IGNORECASE),              # Gemini API keys
    re.compile(r"[0-9]{8,10}:[A-Za-z0-9_\-]{30,}", re.IGNORECASE),      # Telegram Bot Tokens
    re.compile(r"gsk_[A-Za-z0-9_\-]{30,}", re.IGNORECASE),               # Groq API keys
    re.compile(r"sk-or-v1-[A-Za-z0-9_\-]{30,}", re.IGNORECASE),         # OpenRouter API keys
    re.compile(r"[a-f0-9]{32}", re.IGNORECASE),                          # Obsidian 32-hex tokens
]

SENSITIVE_KEYS = {"api_key", "bot_token", "etapi_token", "secret", "token", "password"}


class SecretRedactor:
    """Scans and replaces sensitive tokens in strings, dicts, lists, and stack traces."""

    @staticmethod
    def redact_text(text: str) -> str:
        """Redact known secret token formats from plain text string."""
        if not text or not isinstance(text, str):
            return text

        redacted = text
        for pat in SECRET_PATTERNS:
            def _replacement(match):
                token = match.group(0)
                if len(token) > 8:
                    return token[:4] + "***[REDACTED]***" + token[-4:]
                return "***[REDACTED]***"
            redacted = pat.sub(_replacement, redacted)

        return redacted

    @staticmethod
    def redact_structure(data: Any) -> Any:
        """Recursively redact sensitive values from nested dicts, lists, and objects."""
        if isinstance(data, str):
            return SecretRedactor.redact_text(data)

        elif isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                str_k = str(k).lower()
                if any(sk in str_k for sk in SENSITIVE_KEYS):
                    if isinstance(v, str) and len(v) > 8:
                        new_dict[k] = v[:4] + "***[REDACTED]***" + v[-4:]
                    else:
                        new_dict[k] = "***[REDACTED]***"
                else:
                    new_dict[k] = SecretRedactor.redact_structure(v)
            return new_dict

        elif isinstance(data, list):
            return [SecretRedactor.redact_structure(item) for item in data]

        return data
