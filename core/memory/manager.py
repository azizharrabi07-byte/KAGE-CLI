#!/usr/bin/env python3
"""
manager.py — High-Level Memory Manager Facade for KAGE OS.
Coordinates multi-type memory operations, vector similarity searches, TTL prunings, and importance rankings.
Part of Phase 7 Memory Engine Upgrade.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from .base import MemoryItem, MemoryType
from .store import MemoryStore
from .search import SemanticIndex

logger = logging.getLogger("kage.memory_manager")


class MemoryManager:
    """Production Memory Manager facade exposing unified search, compression, and TTL prunings."""

    def __init__(self, db_store: Optional[MemoryStore] = None):
        self.store = db_store or MemoryStore()
        self.index = SemanticIndex()

    def add_memory(
        self,
        content: str,
        user_id: str = "default",
        memory_type: MemoryType = MemoryType.KNOWLEDGE,
        importance: float = 5.0,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryItem:
        """Create and persist a typed memory record."""
        item = MemoryItem(
            memory_type=memory_type,
            content=content,
            user_id=user_id,
            importance=max(1.0, min(10.0, importance)),
            ttl_seconds=ttl_seconds,
            metadata=metadata or {},
        )
        item_id = self.store.save_item(item)
        item.item_id = item_id

        self.index.index_item(item)
        logger.info(f"Saved memory item {item_id} [{memory_type.value}] for user '{user_id}' (Importance: {importance})")
        return item

    def search_memories(
        self,
        query: str,
        user_id: str = "default",
        top_k: int = 5,
        min_importance: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """Perform similarity search over user memories filtered by importance threshold."""
        user_items = self.store.get_user_items(user_id)
        if not user_items:
            return []

        self.index.index_all([i for i in user_items if i.importance >= min_importance])
        search_results = self.index.search(query, top_k=top_k)

        formatted = []
        for item, similarity in search_results:
            d = item.to_dict()
            d["similarity_score"] = round(similarity, 3)
            formatted.append(d)

        return formatted

    def recall_recent_context(self, user_id: str = "default", limit: int = 10) -> str:
        """Fetch and format recent user items into text context."""
        items = self.store.get_user_items(user_id)
        if not items:
            return f"No active memory context for user '{user_id}'"

        lines = [f"[Recalled Memory Context for {user_id}]:"]
        for i in items[:limit]:
            lines.append(f"• [{i.memory_type.value.upper()}] (Score: {i.importance}) {i.content}")

        return "\n".join(lines)

    def summarize_user_memory(self, user_id: str = "default") -> str:
        """Compress user facts and memories into bullet points."""
        items = self.store.get_user_items(user_id)
        if not items:
            return "No stored user memory."

        important_items = [i for i in items if i.importance >= 4.0]
        summary_lines = [f"Summary of stored memory facts for '{user_id}':"]
        for idx, item in enumerate(important_items, start=1):
            summary_lines.append(f"{idx}. {item.content}")

        return "\n".join(summary_lines)

    def cleanup(self) -> int:
        """Remove expired TTL memory items."""
        return self.store.cleanup_expired()
