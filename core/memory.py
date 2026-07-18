"""
core/memory.py
Core memory (JSON) and memory editing tools for MEMORY.md and USER.md.
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional

KAGE_DIR = Path.home() / ".kage"
MEMORIES_DIR = KAGE_DIR / "memories"
CORE_MEMORY_FILE = KAGE_DIR / "core_memory.json"
MEMORY_FILE = MEMORIES_DIR / "MEMORY.md"
USER_FILE = MEMORIES_DIR / "USER.md"

# ── Core Memory (JSON) ─────────────────────────────────────

def load_core_memory() -> Dict:
    if CORE_MEMORY_FILE.exists():
        try:
            return json.loads(CORE_MEMORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def save_core_memory(data: Dict) -> None:
    CORE_MEMORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def set_core_memory(key: str, value) -> str:
    data = load_core_memory()
    data[key] = value
    save_core_memory(data)
    return f"✅ Core memory updated: `{key}` = `{value}`"


def get_core_memory(key: Optional[str] = None) -> str:
    data = load_core_memory()
    if key:
        return str(data.get(key, f"Key `{key}` not found."))
    return json.dumps(data, indent=2, ensure_ascii=False) if data else "Core memory is empty."


def delete_core_memory(key: str) -> str:
    data = load_core_memory()
    if key in data:
        del data[key]
        save_core_memory(data)
        return f"🗑️ Deleted core memory key: `{key}`"
    return f"Key `{key}` not found."


# ── Markdown Memory ─────────────────────────────────────────

def _ensure_memory_files() -> None:
    MEMORIES_DIR.mkdir(parents=True, exist_ok=True)
    if not MEMORY_FILE.exists():
        MEMORY_FILE.write_text("# KAGE OS — Agent Memory\n\n## Important Facts\n", encoding="utf-8")
    if not USER_FILE.exists():
        USER_FILE.write_text("# KAGE OS — User Profile\n\n## User Information\n", encoding="utf-8")


def _read_md_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _write_md_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def memory_add(content: str, file: str = "memory", section: Optional[str] = None) -> str:
    _ensure_memory_files()
    target = MEMORY_FILE if file == "memory" else USER_FILE
    md_content = _read_md_file(target)
    if section:
        pattern = rf"##\s*{re.escape(section)}.*?(?=##\s|$)"
        match = re.search(pattern, md_content, re.DOTALL | re.IGNORECASE)
        if match:
            new_content = md_content[:match.end()] + f"\n- {content}" + md_content[match.end():]
        else:
            new_content = md_content + f"\n\n## {section}\n- {content}\n"
    else:
        new_content = md_content + f"\n- {content}\n"
    _write_md_file(target, new_content)
    preview = content if len(content) <= 60 else content[:60] + "..."
    return f"✅ Added to {file.upper()}.md: `{preview}`"


def memory_replace(old_content: str, new_content: str, file: str = "memory") -> str:
    _ensure_memory_files()
    target = MEMORY_FILE if file == "memory" else USER_FILE
    md_content = _read_md_file(target)
    if old_content not in md_content:
        return f"❌ Text not found in {file.upper()}.md"
    updated = md_content.replace(old_content, new_content, 1)
    _write_md_file(target, updated)
    return f"✅ Replaced in {file.upper()}.md"


def memory_remove(content_snippet: str, file: str = "memory") -> str:
    _ensure_memory_files()
    target = MEMORY_FILE if file == "memory" else USER_FILE
    md_content = _read_md_file(target)
    lines = md_content.split("\n")
    new_lines = [line for line in lines if content_snippet not in line]
    if len(new_lines) == len(lines):
        return f"❌ Snippet not found in {file.upper()}.md"
    _write_md_file(target, "\n".join(new_lines))
    return f"🗑️ Removed from {file.upper()}.md"


def memory_read(file: str = "memory") -> str:
    _ensure_memory_files()
    target = MEMORY_FILE if file == "memory" else USER_FILE
    return _read_md_file(target)


def memory_search(query: str, file: Optional[str] = None) -> str:
    _ensure_memory_files()
    results = []
    files_to_search = (
        [("memory", MEMORY_FILE), ("user", USER_FILE)]
        if not file
        else [(file, MEMORY_FILE if file == "memory" else USER_FILE)]
    )
    for name, path in files_to_search:
        content = _read_md_file(path)
        if query.lower() in content.lower():
            lines = content.split("\n")
            matching = [l for l in lines if query.lower() in l.lower()]
            results.append(f"**{name.upper()}.md:**\n" + "\n".join(matching))
    return "\n\n".join(results) if results else f"No matches for `{query}`."


# ── Unified Handler ──────────────────────────────────────────

def handle_memory_command(sub_action: str, **kwargs) -> str:
    sub_action = sub_action.lower()
    if sub_action == "add":
        return memory_add(
            kwargs.get("content", ""),
            file=kwargs.get("file", "memory"),
            section=kwargs.get("section"),
        )
    elif sub_action == "replace":
        return memory_replace(
            kwargs.get("old", ""),
            kwargs.get("new", ""),
            file=kwargs.get("file", "memory"),
        )
    elif sub_action == "remove":
        return memory_remove(
            kwargs.get("content", ""),
            file=kwargs.get("file", "memory"),
        )
    elif sub_action == "read":
        return memory_read(file=kwargs.get("file", "memory"))
    elif sub_action == "search":
        return memory_search(kwargs.get("query", ""), file=kwargs.get("file"))
    elif sub_action == "core_write":
        return set_core_memory(kwargs.get("key", ""), kwargs.get("value", ""))
    elif sub_action == "core_read":
        return get_core_memory(kwargs.get("key"))
    elif sub_action == "core_delete":
        return delete_core_memory(kwargs.get("key", ""))
    else:
        return f"❌ Unknown memory command: `{sub_action}`"


if __name__ == "__main__":
    print(memory_add("KAGE uses layered prompts", section="Architecture"))
    print(memory_add("User likes pizza", file="user"))
    print(memory_read("memory"))
    print(memory_search("pizza"))
