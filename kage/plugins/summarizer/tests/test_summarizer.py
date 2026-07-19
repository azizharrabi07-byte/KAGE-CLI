"""Plugin self-test for the summarizer agent."""
from __future__ import annotations
import sys
from pathlib import Path
# repo root = the dir containing the `kage` package
_root = Path(__file__).resolve()
for _p in _root.parents:
    if (_p / "kage" / "__init__.py").exists():
        sys.path.insert(0, str(_p))
        break
from kage.plugins.summarizer.agent import SummarizerAgent

def main() -> int:
    a = SummarizerAgent(); a.wake()
    text = ("Artificial intelligence is transforming how software is built. "
            "Modern systems orchestrate many specialized agents instead of one monolith. "
            "Memory and planning are first-class concerns. " * 3)
    res = a.execute({"text": text, "max_bullets": 3})
    assert res["status"] == "ok", res
    assert 1 <= res["data"]["count"] <= 3, res["data"]
    print(f"summarizer plugin self-test: {res['data']['count']} bullets OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
