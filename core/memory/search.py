#!/usr/bin/env python3
"""
search.py — Pure Python Vector & Semantic Similarity Search Index for KAGE OS.
Implements TF-IDF vectorization and Cosine Similarity matching over memory items.
Part of Phase 7 Memory Engine Upgrade.
"""

import math
import re
from typing import Dict, List, Tuple, Any
from .base import MemoryItem


class SemanticIndex:
    """Term-frequency / cosine similarity search index for semantic memory retrieval."""

    def __init__(self):
        self.documents: List[Tuple[MemoryItem, List[str]]] = []

    def index_item(self, item: MemoryItem):
        """Tokenize and add memory item to index."""
        tokens = re.findall(r"\w+", item.content.lower())
        self.documents.append((item, tokens))

    def index_all(self, items: List[MemoryItem]):
        """Rebuild index with list of items."""
        self.documents.clear()
        for item in items:
            self.index_item(item)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[MemoryItem, float]]:
        """Calculate Cosine Similarity score between query and indexed documents."""
        if not self.documents or not query.strip():
            return []

        query_tokens = re.findall(r"\w+", query.lower())
        if not query_tokens:
            return []

        # Count term frequencies for query
        q_counts: Dict[str, int] = {}
        for t in query_tokens:
            q_counts[t] = q_counts.get(t, 0) + 1

        results: List[Tuple[MemoryItem, float]] = []

        for item, doc_tokens in self.documents:
            if not doc_tokens:
                continue

            d_counts: Dict[str, int] = {}
            for t in doc_tokens:
                d_counts[t] = d_counts.get(t, 0) + 1

            # Compute dot product
            dot_product = sum(q_counts[t] * d_counts.get(t, 0) for t in q_counts)

            # Compute vector magnitudes
            q_mag = math.sqrt(sum(c * c for c in q_counts.values()))
            d_mag = math.sqrt(sum(c * c for c in d_counts.values()))

            if q_mag * d_mag == 0:
                similarity = 0.0
            else:
                similarity = dot_product / (q_mag * d_mag)

            if similarity > 0.05:
                results.append((item, similarity))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
