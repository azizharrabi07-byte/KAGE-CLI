"""agents/security/agent.py — audits code & dependencies for vulnerabilities."""

from __future__ import annotations
import re
from typing import Any, Dict
from ...core.base_agent import BaseAgent

_SUSPICIOUS = [
    re.compile(r"eval\s*\("),
    re.compile(r"exec\s*\("),
    re.compile(r"subprocess\..*shell\s*=\s*True"),
    re.compile(r"password\s*=\s*[\"']"),
    re.compile(r"\b(api_key|secret|token)\s*=\s*[\"'][A-Za-z0-9]{12,}", re.I),
]


class SecurityAgent(BaseAgent):
    name = "security"
    kind = "security"
    description = "Scans source for insecure patterns and exposed secrets."
    emoji = "🛡️"

    def wake(self) -> None:
        self._awake = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        code = str(task.get("code", task.get("content", "")))
        if not code:
            return {"status": "ok", "data": {"findings": [], "count": 0,
                    "risk": "low", "score": 100, "note": "no code supplied"}, "error": None}
        findings = []
        for i, line in enumerate(code.splitlines(), 1):
            for pat in _SUSPICIOUS:
                if pat.search(line):
                    findings.append({"line": i, "pattern": pat.pattern, "snippet": line.strip()[:80]})
        score = max(0, 100 - 12 * len(findings))
        return {"status": "ok", "data": {"findings": findings, "count": len(findings),
                "risk": "high" if findings else "low", "score": score}, "error": None}

    def sleep(self) -> None:
        self._awake = False
