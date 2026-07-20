"""Tests for unified sessions, shared memory attribution, addressable agents.

Run:  python kage/tests/test_unified.py
"""

from __future__ import annotations
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from kage.core.session import SessionStore
from kage.core.memory import MemoryStore
from kage.core.addressing import parse_addressing
from kage.core.session_summary import summarize
from kage.core.registry import AgentRegistry
from kage.core.base_agent import BaseAgent
from kage.core.supervisor import Supervisor

_passed = 0; _failed = 0
def check(name, cond):
    global _passed, _failed
    if cond: _passed += 1
    else: _failed += 1; print(f"  FAIL: {name}")

def test_session_summary_column():
    s = SessionStore(db_path=str(Path(tempfile.mkdtemp()) / "s.db"))
    sid = s.create("u1", title="test")
    check("session created", sid > 0)
    check("summary empty initially", s.get_summary(sid) == "")
    check("summary set", s.set_summary(sid, "Discussed AI trends") is True)
    check("summary retrieved", s.get_summary(sid) == "Discussed AI trends")

def test_session_list_summaries():
    s = SessionStore(db_path=str(Path(tempfile.mkdtemp()) / "s.db"))
    sid1 = s.create("u1", title="s1"); s.set_summary(sid1, "Summary 1")
    s.create("u1", title="s2")
    rows = s.list_summaries("u1")
    check("list_summaries returns rows", len(rows) == 2)
    check("summary in list", any(r["summary"] == "Summary 1" for r in rows))

def test_session_get_single():
    s = SessionStore(db_path=str(Path(tempfile.mkdtemp()) / "s.db"))
    sid = s.create("u1", title="x")
    row = s.get(sid)
    check("get returns row", row is not None and row["title"] == "x")
    check("get missing", s.get(999) is None)

def test_session_message_count():
    s = SessionStore(db_path=str(Path(tempfile.mkdtemp()) / "s.db"))
    sid = s.create("u1")
    s.add_message(sid, "user", "u", "hi")
    s.add_message(sid, "assistant", "Kage", "hello")
    check("message count", s.message_count(sid) == 2)

def test_session_backward_compat():
    s = SessionStore(db_path=str(Path(tempfile.mkdtemp()) / "s.db"))
    sid = s.create("u1", platform="discord", title="chat")
    check("create", sid > 0)
    check("active", s.active("u1") == sid)
    s.add_message(sid, "user", "u1", "hello")
    check("history", len(s.history(sid)) == 1)
    check("list", len(s.list("u1")) == 1)
    check("resume", s.resume(sid) is True)
    check("end", s.end(sid) is True)
    s.close()

def test_migration_on_existing_db():
    d = Path(tempfile.mkdtemp()); db = str(d / "old.db")
    import sqlite3
    conn = sqlite3.connect(db)
    conn.executescript("""CREATE TABLE sessions (id INTEGER PRIMARY KEY, user_id TEXT,
        platform TEXT, title TEXT, status TEXT, created_at REAL, updated_at REAL);
        CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id INTEGER,
        role TEXT, author TEXT, content TEXT, created_at REAL);""")
    conn.execute("INSERT INTO sessions VALUES(1,'u','cli','t','active',1,1)")
    conn.commit(); conn.close()
    s = SessionStore(db_path=db)
    check("migration adds summary col", s.set_summary(1, "ok"))
    check("summary readable after migration", s.get_summary(1) == "ok")
    s.close()

def test_memory_attribution():
    m = MemoryStore(root=str(Path(tempfile.mkdtemp()) / "m"))
    m.set("u", "name", "Kage"); m.set_attribution("u", "name", "Mira")
    check("attribution stored", m.get_attribution("u", "name") == "Mira")
    check("unknown attribution empty", m.get_attribution("u", "unknown") == "")

def test_memory_attributed_get():
    m = MemoryStore(root=str(Path(tempfile.mkdtemp()) / "m"))
    m.set("u", "name", "Kage"); m.set_attribution("u", "name", "Mira")
    m.set("u", "role", "OS"); m.set_attribution("u", "role", "System")
    attr = m.attributed_get("u")
    check("attributed_get agent", attr["name"]["agent"] == "Mira")
    check("attributed_get value", attr["name"]["value"] == "Kage")

def test_memory_forget_clears_attribution():
    m = MemoryStore(root=str(Path(tempfile.mkdtemp()) / "m"))
    m.set("u", "x", "1"); m.set_attribution("u", "x", "Agent")
    check("forget clears", m.forget("u", "x") is True)
    check("attribution gone", m.get_attribution("u", "x") == "")

def test_memory_backward_compat():
    m = MemoryStore(root=str(Path(tempfile.mkdtemp()) / "m"))
    m.set("u", "k", "v")
    check("set/get compat", m.get("u") == {"k": "v"})
    check("forget compat", m.forget("u", "k") is True)

def test_mention_parsing():
    check("@Whiz extracts", parse_addressing("@Whiz weather?", ["whiz"])[0] == "whiz")
    check("@Whiz cleans", parse_addressing("@Whiz weather?", ["whiz"])[1] == "weather?")

def test_agent_command_parsing():
    name, msg = parse_addressing("/agent whiz search AI", ["whiz"])
    check("/agent name", name == "whiz")
    check("/agent message", msg == "search AI")

def test_unknown_mention_ignored():
    check("unknown @ ignored", parse_addressing("@Bob hi", ["whiz"])[0] is None)

def test_no_addressing():
    check("plain text no agent", parse_addressing("hello there", ["whiz"])[0] is None)

def test_summary_heuristic():
    msgs = [{"role": "user", "content": "remember my name is Daddy"}]
    s = summarize(msgs)
    check("summary non-empty", len(s) > 0)

def test_summary_empty():
    check("empty summary", summarize([]) == "")

def test_summary_with_llm():
    def fake_llm(text): return "Brief summary"
    check("LLM summary", summarize([{"role": "user", "content": "t"}], llm=fake_llm) == "Brief summary")

class _WeatherAgent(BaseAgent):
    name = kind = "weather"
    description = "Weather"
    def wake(self): self._awake = True
    def execute(self, task): return {"status": "ok", "data": "Sunny 25C"}
    def sleep(self): self._awake = False

def test_supervisor_mention_routing():
    reg = AgentRegistry(); reg.register(_WeatherAgent)
    sup = Supervisor(registry=reg, memory_store=MemoryStore(root=str(Path(tempfile.mkdtemp())/"m")))
    r = sup.think("@weather what is the temp?", user_id="u")
    check("mention routed", r.agent == "weather" and r.intent == "addressed")

def test_supervisor_agent_command():
    reg = AgentRegistry(); reg.register(_WeatherAgent)
    sup = Supervisor(registry=reg, memory_store=MemoryStore(root=str(Path(tempfile.mkdtemp())/"m")))
    check("slash agent routed", sup.think("/agent weather forecast", user_id="u").agent == "weather")

def test_supervisor_unknown_agent():
    reg = AgentRegistry(); reg.register(_WeatherAgent)
    sup = Supervisor(registry=reg, memory_store=MemoryStore(root=str(Path(tempfile.mkdtemp())/"m")))
    r = sup.think("@nonexistent hello", user_id="u")
    check("unknown agent falls through", r.agent != "nonexistent")

def test_supervisor_memory_attribution():
    reg = AgentRegistry()
    sup = Supervisor(registry=reg, memory_store=MemoryStore(root=str(Path(tempfile.mkdtemp())/"m")))
    sup.think("remember my name is Daddy", user_id="u")
    check("memory has attribution", sup.memory.get_attribution("u", "name") == "Mira")

def test_supervisor_backward_compat():
    reg = AgentRegistry()
    sup = Supervisor(registry=reg, memory_store=MemoryStore(root=str(Path(tempfile.mkdtemp())/"m")))
    check("memory_add still works", sup.think("remember my name is Daddy", user_id="u").intent == "memory_add")
    check("search still routes", sup.think("search AI news", user_id="u").agent == "Whiz")

def test_name_recall_shows_attribution():
    """The attribution (via Mira) should appear even in name-specific recall."""
    reg = AgentRegistry()
    sup = Supervisor(registry=reg, memory_store=MemoryStore(root=str(Path(tempfile.mkdtemp())/"m")))
    sup.think("remember my name is Daddy", user_id="u")
    r = sup.think("what is my name?", user_id="u")
    check("name recall has attribution", "via Mira" in r.text)
    check("name recall has value", "Daddy" in r.text)

def test_general_recall_shows_attribution():
    reg = AgentRegistry()
    sup = Supervisor(registry=reg, memory_store=MemoryStore(root=str(Path(tempfile.mkdtemp())/"m")))
    sup.think("remember my name is Daddy", user_id="u")
    r = sup.think("what do you remember about me?", user_id="u")
    check("general recall has attribution", "via Mira" in r.text)

def test_messages_table_has_agent_column():
    s = SessionStore(db_path=str(Path(tempfile.mkdtemp()) / "s.db"))
    cols = [r[1] for r in s.conn.execute("PRAGMA table_info(messages)")]
    check("messages has agent column", "agent" in cols)

def test_messages_table_has_title_and_summary():
    s = SessionStore(db_path=str(Path(tempfile.mkdtemp()) / "s.db"))
    sid = s.create("u1", title="My Chat")
    cols = [r[1] for r in s.conn.execute("PRAGMA table_info(sessions)")]
    check("sessions has title", "title" in cols)
    check("sessions has summary", "summary" in cols)
    check("title stored", s.get(sid)["title"] == "My Chat")

def test_session_migration_adds_agent_column():
    """Old DB without agent column should auto-migrate."""
    d = Path(tempfile.mkdtemp()); db = str(d / "old2.db")
    import sqlite3
    conn = sqlite3.connect(db)
    conn.executescript("""CREATE TABLE sessions (id INTEGER PRIMARY KEY, user_id TEXT,
        platform TEXT, title TEXT, status TEXT, created_at REAL, updated_at REAL);
        CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id INTEGER,
        role TEXT, author TEXT, content TEXT, created_at REAL);""")
    conn.execute("INSERT INTO sessions VALUES(1,'u','cli','t','active',1,1)")
    conn.commit(); conn.close()
    s = SessionStore(db_path=db)
    cols = [r[1] for r in s.conn.execute("PRAGMA table_info(messages)")]
    check("migration adds agent col to messages", "agent" in cols)
    s.close()

def main() -> int:
    global _failed
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        try: t()
        except Exception as exc:  # noqa: BLE001
            _failed += 1; print(f"  ERROR {t.__name__}: {exc}")
    print(f"\nUnified tests: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0
if __name__ == "__main__": raise SystemExit(main())
