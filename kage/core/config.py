"""core/config.py — configuration loading + first-run wizard.

Reads, in order of precedence: environment variables > ~/.kage/config.yaml
(or json) > defaults. The wizard (``kage config wizard``) writes the file and
optionally ``.env``. Secrets are NEVER written into the repo; the wizard only
touches the user-local config and a git-ignored ``.env``.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict


@dataclass
class Config:
    default_user: str = "cli"
    primary_interface: str = "discord"          # discord | telegram | cli
    use_telegram: bool = False                  # deprecated/optional
    socket_path: str = "~/.kage/kage.sock"
    data_dir: str = "~/.kage"
    log_level: str = "INFO"
    llm_provider: str = "openai"
    # secrets are pulled from env at runtime, never stored in the config dump
    discord_bot_token: str = ""
    discord_webhook_url: str = ""
    telegram_bot_token: str = ""
    web_search_api_key: str = ""
    llm_api_key: str = ""
    agents: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def path(cls) -> Path:
        return Path(os.path.expanduser("~/.kage/config.json"))

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        d = asdict(self)
        if not include_secrets:
            for k in ("discord_bot_token", "discord_webhook_url",
                      "telegram_bot_token", "web_search_api_key", "llm_api_key"):
                d[k] = "***" if d.get(k) else ""
        # expand ~ for display
        d["data_dir"] = os.path.expanduser(self.data_dir)
        d["socket_path"] = os.path.expanduser(self.socket_path)
        return d


def load_config() -> Config:
    cfg = Config()
    p = Config.path()
    if p.exists():
        try:
            data = json.loads(p.read_text())
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
        except (json.JSONDecodeError, OSError):
            pass
    # environment variables override file values (secrets live here)
    env_map = {
        "KAGE_DEFAULT_USER": "default_user",
        "KAGE_PRIMARY_INTERFACE": "primary_interface",
        "KAGE_USE_TELEGRAM": "use_telegram",
        "KAGE_LOG_LEVEL": "log_level",
        "DISCORD_BOT_TOKEN": "discord_bot_token",
        "DISCORD_WEBHOOK_URL": "discord_webhook_url",
        "TELEGRAM_BOT_TOKEN": "telegram_bot_token",
        "WEB_SEARCH_API_KEY": "web_search_api_key",
        "LLM_API_KEY": "llm_api_key",
    }
    for env_key, attr in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            if isinstance(getattr(cfg, attr), bool):
                val = val.lower() in ("1", "true", "yes", "on")
            setattr(cfg, attr, val)
    return cfg


def save_config(cfg: Config) -> Path:
    p = Config.path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg.to_dict(include_secrets=False), indent=2))
    return p


def wizard(interactive: bool = True) -> Config:
    """First-run configuration wizard. Non-interactive uses safe defaults."""
    cfg = load_config()

    def ask(prompt: str, default: str = "") -> str:
        if not interactive:
            return default
        try:
            val = input(f"{prompt} [{default}]: ").strip()
        except EOFError:
            return default
        return val or default

    cfg.primary_interface = ask("Primary interface (discord/telegram/cli)", cfg.primary_interface)
    cfg.use_telegram = ask("Also enable Telegram? (true/false)",
                           str(cfg.use_telegram)).lower() in ("true", "1", "yes")
    cfg.discord_bot_token = os.environ.get("DISCORD_BOT_TOKEN") or ask("DISCORD_BOT_TOKEN", "")
    cfg.llm_api_key = os.environ.get("LLM_API_KEY") or ask("LLM_API_KEY (optional)", "")
    save_config(cfg)
    return cfg
