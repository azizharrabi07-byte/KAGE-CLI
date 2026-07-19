"""Optional workflow definition for the summarizer plugin."""
from __future__ import annotations

WORKFLOW = {
    "name": "summarize-pipeline",
    "entry": "summarize",
    "steps": [
        {"id": "summarize", "name": "Summarize", "agent": "summarizer", "action": "summarize"},
    ],
}
