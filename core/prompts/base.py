#!/usr/bin/env python3
"""
base.py — Modular Prompt Engine Base & Utilities for KAGE OS.
Provides PromptTemplate, PromptVersionRegistry, and PromptCompressor.
Part of Phase 4 Prompt Architecture.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class PromptTemplate:
    """Standardized Prompt Template with variable interpolation and metadata."""
    name: str
    version: str
    template_text: str
    description: str = ""
    required_vars: List[str] = field(default_factory=list)

    def render(self, **kwargs) -> str:
        """Render prompt template substituting variables provided in kwargs."""
        text = self.template_text
        for k, v in kwargs.items():
            val_str = str(v) if v is not None else ""
            text = text.replace(f"{{{{{k}}}}}", val_str).replace(f"${k}", val_str)
        return text


class PromptVersionRegistry:
    """Registry managing versions and variations of system prompts."""

    _templates: Dict[str, Dict[str, PromptTemplate]] = {}

    @classmethod
    def register(cls, template: PromptTemplate):
        """Register a prompt template version."""
        key = template.name.lower()
        if key not in cls._templates:
            cls._templates[key] = {}
        cls._templates[key][template.version] = template

    @classmethod
    def get(cls, name: str, version: str = "latest") -> Optional[PromptTemplate]:
        """Get template version by name."""
        key = name.lower()
        versions = cls._templates.get(key, {})
        if not versions:
            return None
        if version == "latest":
            latest_v = sorted(list(versions.keys()))[-1]
            return versions[latest_v]
        return versions.get(version)


class PromptCompressor:
    """Prunes, summarizes, and compresses context strings to fit within model context limits."""

    @staticmethod
    def compress(text: str, max_chars: int = 4000) -> str:
        """Prunes unnecessary whitespace, removes redundant blank lines, and truncates safely."""
        if not text or len(text) <= max_chars:
            return text

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        pruned = "\n".join(lines)

        if len(pruned) <= max_chars:
            return pruned

        head_len = min(max(10, int(max_chars * 0.4)), max_chars)
        tail_len = max(0, max_chars - head_len - 25)

        if tail_len > 0:
            return pruned[:head_len] + "\n...[Compressed]...\n" + pruned[-tail_len:]
        return pruned[:max_chars]
