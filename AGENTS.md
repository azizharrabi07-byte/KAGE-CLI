# KAGE OS — Agent Instructions

## Available Agents
- browser: Web search and page fetching. Args: {"action": "browser", "query": "..."} or {"action": "browser", "url": "...", "depth": 1}
- memory: Long-term memory management. Args: {"action": "memory", "sub_action": "add|replace|remove", "content": "..."}
- core_memory: Read/write core user identity. Args: {"action": "core_memory", "sub_action": "read|write", "key": "...", "value": "..."}
- session: Session management. Args: {"action": "session", "sub_action": "new|resume|list"}
- openhands: Code execution environment.
- crew: Multi-agent task delegation.

## File Paths
- Config: ~/.kage/
- Memories: ~/.kage/memories/
- Agent definitions: AGENTS.md (project root)
- Core memory: ~/.kage/core_memory.json
- Sessions: ~/.kage/sessions.db
