"""core/supervisor.py — Kage, the supervisor / brain.

This is the heart of KAGE OS. It is **transport-agnostic** and contains no
network/CLI code. On each turn it:

    1. loads per-user context (memory, active session, available agents),
    2. parses the intent of the incoming message,
    3. selects an agent/tool to handle it,
    4. executes (delegating to the chosen agent/tool) with permission gating,
    5. returns a structured ``Response`` the caller (CLI/Discord/Telegram)
       renders however it likes.

The same intent/memory logic is intentionally simple and rule-based so the OS
is fully usable *without* an LLM provider. When an LLM API key is configured,
``llm_complete`` can be wired in to enrich chat/research.
"""

from __future__ import annotations

import logging
import os
import re
import shlex
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .actions import ACTION_SCHEMA, Action, ActionExecutor, format_results, parse_actions
from .addressing import parse_addressing
from .registry import AgentRegistry
from .session_summary import summarize as summarize_session

log = logging.getLogger("kage.supervisor")


# --- Intent model -----------------------------------------------------------

INTENTS = (
    "chat", "search", "research", "memory_add", "memory_recall",
    "agent_list", "system", "session", "workflow", "help", "greeting",
)


@dataclass
class Response:
    """Structured supervisor response, consumed by any transport."""

    text: str
    intent: str = "chat"
    agent: str = "Kage"
    tool: Optional[str] = None
    thinking: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    side_effects: List[Dict[str, Any]] = field(default_factory=list)
    ok: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "intent": self.intent,
            "agent": self.agent,
            "tool": self.tool,
            "thinking": self.thinking,
            "data": self.data,
            "side_effects": self.side_effects,
            "ok": self.ok,
        }


# --- Intent detection -------------------------------------------------------

def detect_intent(text: str) -> str:
    t = (text or "").lower().strip()
    if not t:
        return "chat"

    is_recall = bool(re.search(r"\bwhat\b", t) or re.search(r"\bdo you remember\b", t))
    if (re.search(r"\b(memory|remember)\s+add\b", t) or t.startswith("remember")
            or re.search(r"\bcall me\b", t) or re.search(r"\bmy .+ is\b", t)
            or re.search(r"\bi (like|love|prefer|enjoy)\b", t)
            or re.search(r"\bsave (that|this)\b", t)):
        return "memory_recall" if is_recall else "memory_add"

    if re.search(r"\b(what('s| is| do you know| do you remember)|recall|who am i)\b", t):
        return "memory_recall"

    if re.search(r"\b(research|deep dive|investigate|analyz|analyse)\b", t):
        return "research"

    if re.search(r"\b(search|google|look up|latest|news|find me)\b", t):
        return "search"

    if re.search(r"\b(list|show|available|roster)\b.*\bagents?\b", t) or re.search(
        r"\bagents?\s+(list|status)\b", t
    ):
        return "agent_list"

    if re.search(r"\b(system|health|uptime|diagnostics)\b", t):
        return "system"

    if re.search(r"\bworkflow\b", t):
        return "workflow"

    if re.search(r"\b(new session|switch session|start session|resume session)\b", t):
        return "session"

    if re.search(r"\b(help|commands|what can you do)\b", t):
        return "help"

    if re.match(r"^(hi|hey|hello|yo|sup|good (morning|evening|afternoon))\b", t):
        return "greeting"

    return "chat"


# --- Memory parsing ---------------------------------------------------------

def parse_memory_add(text: str) -> Optional[Dict[str, str]]:
    t = text.strip()
    m = re.search(r"memory\s+add\s+(\S+)\s+(.+)", t, re.I)
    if m:
        return {"key": m.group(1).lower(), "value": _clean(m.group(2))}
    m = re.search(r"call me\s+(.+)", t, re.I)
    if m:
        return {"key": "name", "value": _clean(m.group(1))}
    m = re.search(r"my name is\s+(.+)", t, re.I)
    if m:
        return {"key": "name", "value": _clean(m.group(1))}
    m = re.search(r"my\s+([a-z][\w\s-]*?)\s+is\s+(.+)", t, re.I)
    if m:
        return {"key": m.group(1).strip(), "value": _clean(m.group(2))}
    m = re.search(r"i\s+(like|love|prefer|enjoy)\s+(.+)", t, re.I)
    if m:
        return {"key": "likes", "value": _clean(m.group(2))}
    m = re.search(r"\b(remember|note|save)\s+(that|down|this)?\s*(.+)", t, re.I)
    if m and m.group(3):
        return {"key": "note", "value": _clean(m.group(3))}
    return None


def _clean(v: str) -> str:
    return re.sub(r"\bplease\b", "", v, flags=re.I).strip().rstrip(".!?")


def recall_memory(memory: Dict[str, str], text: str) -> Optional[str]:
    if not memory:
        return None
    t = text.lower()
    if re.search(r"\b(my name|who am i)\b", t):
        return memory.get("name") or next((v for k, v in memory.items() if "name" in k), None)
    if re.search(r"\bwhat do you (know|remember)\b", t):
        return "; ".join(f"{k}: {v}" for k, v in memory.items())
    m = re.search(r"what(?:'s| is| are) my\s+([a-z][\w\s-]*)", t)
    if m:
        wanted = m.group(1).strip()
        for k, v in memory.items():
            if k == wanted or wanted in k or k in wanted:
                return v
    return None


# --- The supervisor ---------------------------------------------------------

class Supervisor:
    """The brain. Wires together the agent registry, memory, sessions, tools."""

    def __init__(
        self,
        registry: AgentRegistry,
        memory_store: Any = None,
        session_store: Any = None,
        tools: Any = None,
        security: Any = None,
        config: Optional[Dict[str, Any]] = None,
        # Optional LLM callable: llm(message, context) -> str. When provided,
        # open chat + research delegate to it (e.g. the existing core.brain.Brain).
        llm: Optional[Any] = None,
    ) -> None:
        self.registry = registry
        self.memory = memory_store
        self.sessions = session_store
        self.tools = tools
        self.security = security
        self.config = config or {}
        self.llm = llm
        # The "user" is identified by transport user id (Discord snowflake,
        # telegram id, "cli" for local). Memory/sessions are keyed on it.
        self.default_user = self.config.get("default_user", "cli")
        # Action executor: lets Kage ACT (shell / file_edit / create_agent).
        self.executor = ActionExecutor(
            root=self.config.get("root", "") or os.environ.get("KAGE_ROOT", ""),
            allow_all=bool(self.config.get("allow_destructive", False)),
        )

    # -- context -------------------------------------------------------------
    def context_for(self, user_id: str) -> Dict[str, Any]:
        memory = self.memory.get(user_id) if self.memory else {}
        return {
            "user_id": user_id,
            "user_name": memory.get("name"),
            "memory": memory,
            "agents": self.registry.all_info(),
        }

    def _llm_context(self, ctx: Dict[str, Any]) -> str:
        """Build a compact context string injected into LLM prompts."""
        bits = []
        if ctx.get("user_name"):
            bits.append(f"User name: {ctx['user_name']}")
        if ctx.get("memory"):
            mem = "; ".join(f"{k}={v}" for k, v in ctx["memory"].items())
            bits.append(f"Known memory: {mem}")
        return " | ".join(bits)

    # -- main entry ----------------------------------------------------------
    def think(self, message: str, user_id: Optional[str] = None,
              target_agent: Optional[str] = None) -> Response:
        """Run one supervisor turn.

        When ``target_agent`` is set (via @mention or /agent), the message is
        routed directly to that agent instead of the default intent logic.
        """
        uid = user_id or self.default_user
        ctx = self.context_for(uid)

        addressed = target_agent
        cleaned = message
        if not addressed:
            known = self.registry.list() if self.registry else []
            addressed, cleaned = parse_addressing(message, known)
        if addressed:
            return self._delegate_to_agent(addressed, cleaned, uid, ctx)

        intent = detect_intent(message)
        thinking = [f"parsed intent → {intent}"]
        user_name = ctx["user_name"]

        if intent == "memory_add":
            parsed = parse_memory_add(message)
            if not parsed:
                return Response(
                    'Could not parse a key/value. Try: "remember my name is Daddy".',
                    intent="memory_add", agent="Kage", thinking=thinking, ok=False,
                )
            thinking.append(f'extracted {parsed["key"]} = "{parsed["value"]}"')
            if self.security and not self.security.allow("memory.add", uid):
                return Response("Permission denied for memory.add.", intent=intent,
                                agent="Kage", thinking=thinking, ok=False)
            if self.memory:
                self.memory.set(uid, parsed["key"], parsed["value"])
                if hasattr(self.memory, "set_attribution"):
                    self.memory.set_attribution(uid, parsed["key"], "Mira")
            return Response(
                f'Stored **{parsed["key"]}** = `{parsed["value"]}` in long-term memory. 🧠',
                intent="memory_add", agent="Mira", tool="memory.add", thinking=thinking,
            )

        if intent == "memory_recall":
            value = recall_memory(ctx["memory"], message)
            thinking.append("found memory" if value else "no matching memory")
            if value and re.search(r"\b(my name|who am i)\b", message.lower()):
                text = f"Your name is **{value}**. 🧠"
            elif value:
                agent_src = ""
                if hasattr(self.memory, "get_attribution"):
                    for k, v in ctx["memory"].items():
                        if v == value:
                            agent_src = self.memory.get_attribution(uid, k)
                            break
                src_tag = f" (via {agent_src})" if agent_src else ""
                text = f"From memory: **{value}**. 🧠{src_tag}"
            else:
                text = ("I don't have that in memory yet. Tell me with "
                        '"remember …" or "memory add <key> <value>".')
            return Response(text, intent="memory_recall", agent="Mira",
                            tool="memory.recall", thinking=thinking)

        if intent == "search":
            thinking.append("routing to web agent (Whiz)")
            result = self._delegate("whatsapp", None)  # placeholder fallback
            return Response(self._search_text(message), intent="search", agent="Whiz",
                            tool="web.search", thinking=thinking,
                            data=result, side_effects=[{"type": "relay",
                                    "channel": "web-search", "message": f"🔎 {message}"}])

        if intent == "research":
            thinking.append("routing to research agent (Sage)")
            return Response(self._research_text(message), intent="research", agent="Sage",
                            tool="research.run", thinking=thinking,
                            side_effects=[{"type": "relay", "channel": "deep-research",
                                    "message": f"🔬 {message}"}])

        if intent == "agent_list":
            thinking.append("composing roster")
            return Response(self._list_agents(ctx["agents"]), intent="agent_list",
                            agent="Kage", thinking=thinking)

        if intent == "system":
            thinking.append("asking system agent (Sentinel)")
            return Response(self._system_report(ctx["agents"]), intent="system",
                            agent="Sentinel", tool="system.report", thinking=thinking)

        if intent == "session":
            thinking.append("session control")
            return Response("Starting a fresh session. Memory is preserved.",
                            intent="session", agent="Kage", thinking=thinking,
                            side_effects=[{"type": "session_new"}])

        if intent == "workflow":
            thinking.append("workflow reference")
            return Response("Run workflows with: `kage workflow run <file.json>`.",
                            intent="workflow", agent="Kage", thinking=thinking)

        if intent == "help":
            thinking.append("help index")
            return Response(self._help_text(), intent="help", agent="Kage", thinking=thinking)

        if intent == "greeting":
            thinking.append(f"greeting {user_name or 'new user'}")
            text = (f"Hey **{user_name}**! 👋 I'm Kage. What can I do for you?"
                    if user_name else "Hey! 👋 I'm **Kage**, your supervisor. Type `help`.")
            return Response(text, intent="greeting", agent="Kage", thinking=thinking)

        # default: chat — use the LLM brain if one is wired (e.g. core.brain.Brain)
        thinking.append("synthesizing supervisor reply")
        reply = None
        if self.llm is not None:
            try:
                context = self._llm_context(ctx) + "\n\n" + ACTION_SCHEMA
                reply = self.llm(message, context)
            except Exception as exc:  # noqa: BLE001 — fall back to rule-based reply
                thinking.append(f"llm failed ({exc}); using fallback")
                reply = None

        # Kage is proactive: parse + execute any action in the reply (LLM JSON),
        # or fall back to lightweight rule-based actions when no LLM is wired.
        text, effects = self._run_actions(reply or "", message, uid, thinking)
        if effects:
            self._register_new_agents(effects)
            base = (reply and parse_actions(reply)[1]) or ""
            body = (base + "\n\n" + format_results(effects)).strip()
            return Response(body or "Done.", intent="chat", agent="Kage",
                            thinking=thinking, side_effects=effects)
        if reply:
            return Response(reply, intent="chat", agent="Kage", thinking=thinking)
        return Response(self._chat_text(message, user_name), intent="chat",
                        agent="Kage", thinking=thinking)

    # -- action execution ----------------------------------------------------
    def _run_actions(self, reply: str, message: str, uid: str,
                     thinking: List[str]) -> tuple:
        """Execute actions parsed from an LLM reply, or rule-based fallback.

        Returns (display_text_unused, side_effects). Only acts when an action is
        actually present, so normal chat is unaffected.
        """
        actions = parse_actions(reply)[0]
        if not actions and self.llm is None:
            actions = self._rule_actions(message)
        if not actions:
            return reply, []
        thinking.append(f"executing {len(actions)} action(s)")
        effects: List[Dict[str, Any]] = []
        for act in actions:
            try:
                res = self.executor.execute(act)
            except Exception as exc:  # noqa: BLE001 — never crash a turn
                res = {"ok": False, "kind": act.kind, "error": str(exc)}
            effects.append(res)
        return reply, effects

    def _rule_actions(self, message: str) -> List[Action]:
        """No-LLM fallback intents so Kage can still ACT without a provider."""
        low = message.lower()
        actions: List[Action] = []
        if (re.search(r"\b(list|show|ls|dir)\b", low)
                and re.search(r"\b(files?|folders?|dir|directory|contents?)\b", low)
                and "agent" not in low):
            path = self._extract_path(message)
            actions.append(Action("shell", {"command": f"ls -la {shlex.quote(path)}"}))
        m = re.search(r"\bcreate\b.*?\bagent\b.*?\b(?:called|named)\s+([A-Za-z0-9_]+)", low)
        if m:
            actions.append(Action("create_agent", {"name": m.group(1)}))
        return actions

    @staticmethod
    def _extract_path(message: str) -> str:
        """Best-effort path token from a 'list files' request."""
        m = re.search(r"(~[A-Za-z0-9_./-]+|[A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+)", message)
        if m:
            return m.group(1)
        return "~" if "home" in message.lower() else "."

    def _register_new_agents(self, effects: List[Dict[str, Any]]) -> None:
        """Best-effort discovery+register of agents just scaffolded."""
        for fx in effects:
            if fx.get("kind") == "create_agent" and fx.get("ok") and fx.get("register"):
                try:
                    self.registry.discover([fx["register"]])
                except Exception:  # noqa: BLE001
                    pass

    def _delegate_to_agent(self, name: str, message: str, uid: str,
                           ctx: Dict[str, Any]) -> Response:
        """Route a message to a specific addressed agent."""
        agent = self.registry.get(name, supervisor=self)
        if agent is None:
            return Response(f"Agent '{name}' not found. Available: "
                            f"{', '.join(self.registry.list())}",
                            intent="agent_not_found", agent="Kage", ok=False)
        if not agent.is_awake:
            try:
                agent.wake()
            except Exception as exc:  # noqa: BLE001
                return Response(f"Agent '{name}' failed to wake: {exc}",
                                agent="Kage", ok=False)
        try:
            result = agent.execute({"goal": message, "message": message,
                                    "user_id": uid, "context": ctx})
            text = ""
            if isinstance(result, dict):
                text = str(result.get("text", result.get("data", result)))
            else:
                text = str(result)
            return Response(text, intent="addressed", agent=agent.name,
                            thinking=[f"delegated to {name}"])
        except Exception as exc:  # noqa: BLE001
            return Response(f"Agent '{name}' errored: {exc}", agent="Kage", ok=False)

    # -- delegation to agents/tools -----------------------------------------
    def _delegate(self, agent_name: Optional[str], task: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Best-effort execution via the agent registry; never raises."""
        if not agent_name:
            return {}
        try:
            agent = self.registry.get(agent_name, supervisor=self)
            if not agent:
                return {}
            if not agent.is_awake:
                agent.wake()
            return agent.execute(task or {}) or {}
        except Exception as exc:  # noqa: BLE001
            log.warning("agent %s failed: %s", agent_name, exc)
            return {"error": str(exc)}

    def run_tool(self, name: str, args: Dict[str, Any], user_id: str = "cli") -> Dict[str, Any]:
        """Permission-gated tool execution returning structured output."""
        if self.security and not self.security.allow(name, user_id):
            return {"ok": False, "error": f"permission denied: {name}"}
        if not self.tools:
            return {"ok": False, "error": "no tools registered"}
        return self.tools.run(name, args, user_id=user_id)

    # -- text composers ------------------------------------------------------
    @staticmethod
    def _list_agents(agents: List[Dict[str, Any]]) -> str:
        lines = ["Crew (each agent owns a channel/domain):", ""]
        for i, a in enumerate(agents, 1):
            lines.append(f'{i}. {a.get("emoji","🤖")} {a["name"]} — {a.get("kind","?")} '
                         f'· {"awake" if a.get("awake") else "asleep"}')
        lines.append("")
        lines.append("Route work to any of them through me.")
        return "\n".join(lines)

    @staticmethod
    def _system_report(agents: List[Dict[str, Any]]) -> str:
        awake = sum(1 for a in agents if a.get("awake"))
        return (f"🛡️ System Report\n- agents awake: {awake}/{len(agents)}\n"
                "- primary interface: discord\n- telegram: optional/deprecated\n"
                "- supervisor: online, accepting work")

    @staticmethod
    def _search_text(text: str) -> str:
        q = re.sub(r"^(search|google|look up|find me)\s+", "", text, flags=re.I).strip().rstrip(".?!")
        return (f"🌐 Whiz — Web Search\nquery: {q or '—'}\n\n"
                "1. query search provider\n2. filter for relevance/freshness\n3. summarize\n\n"
                "Set WEB_SEARCH_API_KEY for live sources.")

    @staticmethod
    def _research_text(text: str) -> str:
        q = re.sub(r"^(research|deep dive|investigate|analyz|analyse)\s+", "", text, flags=re.I).strip().rstrip(".?!")
        return (f"🔬 Sage — Deep Research\ntopic: {q or '—'}\n\n"
                "1. decompose → sub-questions\n2. gather evidence\n3. cross-check\n4. synthesize report\n\n"
                "Set LLM_API_KEY for fully live research.")

    @staticmethod
    def _help_text() -> str:
        return ("\nKage commands (also slash commands in Discord):\n"
                "  chat <msg>        talk to me\n"
                "  search <q>        web search (Whiz)\n"
                "  research <q>      deep research (Sage)\n"
                "  memory add <k> <v> remember a fact (Mira)\n"
                "  agents            list the crew\n"
                "  system            health report (Sentinel)\n"
                "  session new       start a session\n"
                "  help              this message")

    @staticmethod
    def _chat_text(message: str, user_name: Optional[str]) -> str:
        name_bit = f" {user_name}" if user_name else ""
        return (f"Hey{name_bit} — got it.\n\n"
                "I can: search (Whiz), research (Sage), remember (Mira), "
                "or just chat. Tell me which direction.")
