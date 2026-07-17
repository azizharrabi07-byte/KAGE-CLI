#!/usr/bin/env python3
"""
context_builder.py — Dynamic Prompt Context Assembly Engine for KAGE OS.
Combines system templates, per-user memory context, tool schemas, and chat history.
Part of Phase 4 Prompt Architecture.
"""

from typing import Dict, List, Optional, Any
from .base import PromptTemplate, PromptVersionRegistry, PromptCompressor
from core.user_memory import format_user_memory_prompt


class ContextBuilder:
    """Assembles structured prompt messages and context budgets for LLM calls."""

    def __init__(self, system_template_name: str = "system", version: str = "latest"):
        template = PromptVersionRegistry.get(system_template_name, version)
        self.system_template = template or PromptVersionRegistry.get("system", "v2.1")
        self.compressor = PromptCompressor()

    def build_system_instruction(self, user_id: str = "default", extra_instructions: str = "") -> str:
        """Render full system instruction string including user memory and active rules."""
        base_system = self.system_template.render()
        memory_context = format_user_memory_prompt(user_id)

        full_system = f"{base_system}\n\n{memory_context}"
        if extra_instructions:
            full_system += f"\n\nADDITIONAL INSTRUCTIONS:\n{extra_instructions}"

        return full_system

    def build_messages(
        self,
        user_query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        max_context_chars: int = 8000,
    ) -> List[Dict[str, str]]:
        """Assemble conversation payload within specified character context limits."""
        messages = []

        if chat_history:
            for msg in chat_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": self.compressor.compress(msg.get("content", ""), max_chars=2000)
                })

        messages.append({
            "role": "user",
            "content": self.compressor.compress(user_query, max_chars=max_context_chars)
        })

        return messages
