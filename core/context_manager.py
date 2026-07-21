import json
import os
import tomllib
from pathlib import Path
from typing import Any

KAGE_HOME = Path(os.environ.get("KAGE_HOME", Path.home() / "kage-os"))

LEVEL1_TRIGGERS = {"remember", "earlier", "history", "continue"}
LEVEL3_SESSION = {"remember", "earlier", "history", "continue"}
LEVEL3_WORKFLOW = {"workflow", "pipeline", "run", "schedule"}
LEVEL3_MEMORY = {"notes", "memories", "obsidian", "vault"}


class ContextManager:
    def __init__(self):
        self._identity_agent: str = ""
        self._identity_user: str = ""
        self._config_env: dict[str, str] = {}
        self._skills_manifest: dict[str, Any] = {}
        self._system_rules: dict[str, Any] = {}
        self._loaded = False

    def load_level1(self):
        agent_path = KAGE_HOME / "identity" / "agent_identity.md"
        user_path = KAGE_HOME / "identity" / "user_identity.md"
        if agent_path.exists():
            self._identity_agent = agent_path.read_text().strip()
        if user_path.exists():
            self._identity_user = user_path.read_text().strip()

    def load_level2(self):
        env_path = KAGE_HOME / "config" / ".env"
        if env_path.exists():
            for line in env_path.read_text().strip().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    self._config_env[k.strip()] = v.strip()

        manifest_path = KAGE_HOME / "config" / "skills_manifest.json"
        if manifest_path.exists():
            self._skills_manifest = json.loads(manifest_path.read_text())

        rules_path = KAGE_HOME / "config" / "system_rules.toml"
        if rules_path.exists():
            with open(rules_path, "rb") as f:
                self._system_rules = tomllib.load(f)

    def load_all(self) -> "ContextManager":
        self.load_level1()
        self.load_level2()
        self._loaded = True
        return self

    def get_default_context(self) -> dict[str, Any]:
        if not self._loaded:
            self.load_all()
        return {
            "agent": self._identity_agent,
            "user": self._identity_user,
            "skills": self._skills_manifest,
            "rules": self._system_rules,
        }

    def get_context(self, user_prompt: str, session_id: str | None = None) -> dict[str, Any]:
        context = self.get_default_context()
        context["session"] = None
        context["workflow"] = None
        context["memory"] = None

        lowered = user_prompt.lower()

        if any(w in lowered for w in LEVEL3_SESSION):
            context["session"] = self._load_session(session_id) if session_id else self._load_latest_session()

        if any(w in lowered for w in LEVEL3_WORKFLOW):
            context["workflow"] = self._load_workflow_list()

        if any(w in lowered for w in LEVEL3_MEMORY):
            context["memory"] = self._load_recent_memories()

        return context

    def _load_session(self, session_id: str) -> str | None:
        path = KAGE_HOME / "sessions" / f"{session_id}.json"
        if path.exists():
            return path.read_text()
        return None

    def _load_latest_session(self) -> str | None:
        sessions_dir = KAGE_HOME / "sessions"
        if not sessions_dir.exists():
            return None
        files = sorted(sessions_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
        if files:
            return files[0].read_text()
        return None

    def _load_workflow_list(self) -> list[str]:
        wf_dir = KAGE_HOME / "workflows"
        if not wf_dir.exists():
            return []
        return sorted(f.name for f in wf_dir.glob("*.json"))

    def _load_recent_memories(self) -> str | None:
        mem_path = KAGE_HOME / "long_term" / "memories.md"
        if mem_path.exists():
            return mem_path.read_text()
        return None

    @property
    def default_context_token_estimate(self) -> int:
        total = len(self._identity_agent) + len(self._identity_user)
        total += len(json.dumps(self._skills_manifest))
        total += len(json.dumps(self._system_rules))
        return total // 4
