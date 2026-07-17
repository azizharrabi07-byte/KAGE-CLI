"""
KAGE OS Modular Prompt Architecture Package.
Provides templates, version management, prompt compression, and context assembly.
"""

from .base import PromptTemplate, PromptVersionRegistry, PromptCompressor
from .templates import (
    SYSTEM_PROMPT,
    DEVELOPER_PROMPT,
    TOOL_PROMPT,
    PLANNER_PROMPT,
    REASONING_PROMPT,
    MEMORY_PROMPT,
    SUMMARIZER_PROMPT,
    AGENT_PROMPT,
    REFLECTION_PROMPT,
    EXECUTION_PROMPT,
    SAFETY_PROMPT,
    ERROR_RECOVERY_PROMPT,
)
from .context_builder import ContextBuilder

__all__ = [
    "PromptTemplate",
    "PromptVersionRegistry",
    "PromptCompressor",
    "ContextBuilder",
    "SYSTEM_PROMPT",
    "DEVELOPER_PROMPT",
    "TOOL_PROMPT",
    "PLANNER_PROMPT",
    "REASONING_PROMPT",
    "MEMORY_PROMPT",
    "SUMMARIZER_PROMPT",
    "AGENT_PROMPT",
    "REFLECTION_PROMPT",
    "EXECUTION_PROMPT",
    "SAFETY_PROMPT",
    "ERROR_RECOVERY_PROMPT",
]
