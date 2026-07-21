from core.context_manager import ContextManager, KAGE_HOME


class Brain:
    def __init__(self, ctx: ContextManager | None = None):
        self.ctx = ctx or ContextManager().load_all()

    def build_system_prompt(self, user_prompt: str, session_id: str | None = None) -> str:
        context = self.ctx.get_context(user_prompt, session_id)
        base = context["agent"]
        parts = [base, "", "---", "", context["user"]]

        skills_list = context["skills"].get("skills", [])
        if skills_list:
            names = ", ".join(s["id"] for s in skills_list)
            parts.append(f"\nAvailable Skills: {names}")

        if context["session"]:
            parts.append(f"\n[Session Context Loaded]\n{context['session']}")

        if context["workflow"]:
            parts.append(f"\n[Available Workflows]\n" + "\n".join(f"  - {w}" for w in context["workflow"]))

        if context["memory"]:
            parts.append(f"\n[Long-Term Memories]\n{context['memory']}")

        parts.append("\n---\nRespond concisely and directly.")
        return "\n".join(parts)

    def token_estimate(self) -> int:
        return self.ctx.default_context_token_estimate

    def session_dir(self):
        return KAGE_HOME / "sessions"

    def log_session(self, session_id: str, prompt: str, response: str):
        import json, datetime
        self.session_dir().mkdir(parents=True, exist_ok=True)
        path = self.session_dir() / f"{session_id}.json"
        data = {
            "id": session_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt": prompt,
            "response": response,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
