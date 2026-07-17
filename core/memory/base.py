#!/usr/bin/env python3
"""
base.py — Base Types & MemoryItem Definitions for KAGE OS Memory System.
Supports 5 memory types: Conversation, Knowledge, Working, Episodic, and Semantic.
Part of Phase 7 Memory Engine Upgrade.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any


class MemoryType(Enum):
    CONVERSATION = "conversation"  # Short-term chat history
    KNOWLEDGE = "knowledge"        # Structured domain facts
    WORKING = "working"            # Active task / execution context buffer
    EPISODIC = "episodic"          # Timestamped event logs with importance score
    SEMANTIC = "semantic"          # Vector / similarity indexed memory


@dataclass
class MemoryItem:
    """Standardized memory record with importance scoring and TTL expiration."""
    memory_type: MemoryType
    content: str
    user_id: str = "default"
    importance: float = 5.0  # Scale 1.0 (trivial) to 10.0 (critical)
    ttl_seconds: Optional[int] = None  # None = permanent, int = expires after N seconds
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None
    item_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.ttl_seconds and not self.expires_at:
            exp = datetime.now() + timedelta(seconds=self.ttl_seconds)
            self.expires_at = exp.isoformat()

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now().isoformat() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.item_id,
            "type": self.memory_type.value,
            "user_id": self.user_id,
            "content": self.content,
            "importance": round(self.importance, 1),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }
