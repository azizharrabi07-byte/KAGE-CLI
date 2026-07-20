"""core/addressing.py — parse @mentions and /agent commands for routing.

When a user addresses a specific agent (e.g. ``@Whiz what is the weather?`` or
``/agent whiz search AI news``), the supervisor delegates to that agent instead
of its default routing. This extracts the target agent + cleaned message.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

_MENTION_RE = re.compile(r"(?:^|\s)@([A-Za-z_][\w-]*)", re.MULTILINE)
_AGENT_CMD_RE = re.compile(r"^/agent\s+([A-Za-z_][\w-]*)\s+(.+)", re.IGNORECASE | re.DOTALL)


def parse_addressing(text: str, known_agents: Optional[list] = None) -> Tuple[Optional[str], str]:
    """Extract an addressed agent and the cleaned message.

    Returns (agent_name_or_None, cleaned_message). When no agent is addressed,
    returns (None, original_text).
    """
    if not text:
        return None, text

    m = _AGENT_CMD_RE.match(text.strip())
    if m:
        name = m.group(1).lower()
        msg = m.group(2).strip()
        if not known_agents or name in [a.lower() for a in known_agents]:
            return name, msg

    m = _MENTION_RE.search(text)
    if m:
        name = m.group(1).lower()
        if known_agents and name not in [a.lower() for a in known_agents]:
            return None, text
        cleaned = _MENTION_RE.sub(" ", text).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return name, cleaned or text

    return None, text
