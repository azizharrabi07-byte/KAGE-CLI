"""agents/meta/agent.py — self-upgrade & crew reflection (Meta).

  * upgrade.check  — is the repo behind origin?
  * upgrade.apply  — pull + run tests; REQUIRES confirm=True
  * crew           — reflect on the registered agents.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any, Dict, Optional

from ...core.base_agent import BaseAgent


class MetaAgent(BaseAgent):
    name = "meta"
    kind = "meta"
    description = "Self-upgrade (git pull + tests) and crew reflection."
    emoji = "🪞"

    def wake(self) -> None:
        self._awake = True
        self._repo = self.config.get("repo_root", ".")

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        op = str(task.get("op", task.get("action", "crew")))
        if op in ("crew", "meta.crew"):
            agents = self.supervisor.registry.list() if self.supervisor else []
            return {"status": "ok", "data": {"agents": agents, "count": len(agents)}, "error": None}
        if op in ("upgrade.check", "upgrade", "meta.upgrade.check"):
            return {"status": "ok", "data": self.check_upgrade(), "error": None}
        if op in ("upgrade.apply", "meta.upgrade.apply"):
            return self.apply_upgrade(confirm=bool(task.get("confirm", False)),
                                      run_tests=bool(task.get("run_tests", True)))
        return {"status": "error", "data": None, "error": f"unknown meta op: {op}"}

    def check_upgrade(self) -> Dict[str, Any]:
        if not self._has_git():
            return {"available": False, "error": "git not found", "source": "unavailable"}
        if not self._is_repo():
            return {"available": False, "error": "not a git repository", "source": "unavailable"}
        self._git("fetch", "--quiet")
        local = self._git("rev-parse", "HEAD")
        remote = self._git("rev-parse", "@{u}", allow_fail=True) or self._git("rev-parse", "origin/HEAD")
        behind = self._git("rev-list", "--count", f"{local}..{remote}", allow_fail=True) if remote else "0"
        return {"available": int(behind or 0) > 0, "local": local, "remote": remote,
                "commits_behind": int(behind or 0), "source": "git"}

    def apply_upgrade(self, *, confirm: bool, run_tests: bool) -> Dict[str, Any]:
        info = self.check_upgrade()
        if not info.get("available"):
            return {"status": "ok", "data": info | {"applied": False, "note": "already up to date"}, "error": None}
        if not confirm:
            return {"status": "error", "data": info, "error": "upgrade requires explicit confirm=True"}
        pull = self._git("pull", "--ff-only")
        tests = None
        if run_tests:
            tests = self._run_tests()
            if tests and not tests.get("ok"):
                return {"status": "error", "data": {"pull": pull, "tests": tests},
                        "error": "tests failed after upgrade; review before restarting"}
        return {"status": "ok", "data": {"applied": True, "pull": pull, "tests": tests}, "error": None}

    def _run_tests(self) -> Optional[Dict[str, Any]]:
        import sys
        try:
            proc = subprocess.run([sys.executable, "kage/tests/test_phases_3_8.py"],
                                  capture_output=True, text=True, timeout=120, cwd=self._repo)
            return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout_tail": proc.stdout[-400:]}
        except (subprocess.TimeoutExpired, OSError) as exc:
            return {"ok": False, "error": str(exc)}

    def _git(self, *args: str, allow_fail: bool = False) -> str:
        try:
            proc = subprocess.run(["git", "-C", self._repo, *args],
                                  capture_output=True, text=True, timeout=20, check=False)
            if proc.returncode != 0 and not allow_fail:
                return ""
            return proc.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return ""

    def _has_git(self) -> bool:
        return shutil.which("git") is not None

    def _is_repo(self) -> bool:
        return bool(self._git("rev-parse", "--is-inside-work-tree"))

    def sleep(self) -> None:
        self._awake = False
