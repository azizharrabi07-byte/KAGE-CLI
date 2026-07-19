"""Plugin: summarizer — condenses long text into bullet summaries."""

from __future__ import annotations
import re
from typing import Any, Dict, List

try:
    from kage.core.base_agent import BaseAgent  # type: ignore
except ImportError:  # imported within the kage package layout
    from ...core.base_agent import BaseAgent  # type: ignore


class SummarizerAgent(BaseAgent):
    name = "summarizer"
    kind = "summarizer"
    description = "Condenses long text into concise bullet summaries."
    emoji = "📝"

    def wake(self) -> None:
        self._awake = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        text = str(task.get("text", task.get("content", "")))
        bullets = self.summarize(text, max_bullets=int(task.get("max_bullets", 5)))
        return {"status": "ok", "data": {"bullets": bullets, "count": len(bullets)}, "error": None}

    @staticmethod
    def summarize(text: str, max_bullets: int = 5) -> List[str]:
        """Deterministic extractive summary (no LLM required)."""
        sentences = re.split(r"(?<=[.!?])\s+", (text or "").strip())
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        if not sentences:
            return []
        # rank by length-information heuristic (longer, earlier sentences first)
        ranked = sorted(enumerate(sentences), key=lambda x: (-len(x[1]), x[0]))
        picked = sorted(ranked[:max_bullets], key=lambda x: x[0])
        return [f"• {s}" for _, s in picked]

    def sleep(self) -> None:
        self._awake = False
