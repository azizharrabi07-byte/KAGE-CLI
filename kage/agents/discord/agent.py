"""agents/discord/agent.py — Discord bot, the PRIMARY interface for KAGE OS.

Uses discord.py 2.x. This is a pure transport: it receives messages and slash
commands, hands them to the supervisor (core.supervisor.Supervisor), applies
returned side effects (memory, relay, session), and posts the reply.

Lifecycle: wake() (login + sync commands) -> execute() (bot loop) -> sleep().

Requires discord.py:  pip install discord.py
Run via:  kage discord start   (or)   kage run --interface discord
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ...core.base_agent import BaseAgent

log = logging.getLogger("kage.discord")


class DiscordAgent(BaseAgent):
    """discord.py transport implementing the agent lifecycle."""

    name = "discord"
    kind = "discord"
    description = "Primary Discord interface with /kage slash commands."
    emoji = "🎮"

    def wake(self) -> None:
        # Imported lazily so the rest of the OS works without discord.py.
        import discord
        from discord import app_commands

        token = (self.config.get("token")
                 or _env("DISCORD_BOT_TOKEN"))
        if not token:
            raise RuntimeError("DISCORD_BOT_TOKEN is required for the Discord agent")

        intents = discord.Intents.default()
        intents.message_content = True  # privileged: enable in Developer Portal
        self.bot = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.bot)
        self.token = token
        self._register_commands()

        @self.bot.event
        async def on_ready() -> None:
            try:
                synced = await self.tree.sync()
                log.info("synced %d slash commands as %s", len(synced), self.bot.user)
            except Exception as exc:  # noqa: BLE001
                log.error("slash sync failed: %s", exc)
            self._awake = True
            log.info("Discord online as %s", self.bot.user)

        @self.bot.event
        async def on_message(message):  # type: ignore[no-untyped-def]
            await self._on_message(message)

    # -- slash commands ------------------------------------------------------
    def _register_commands(self) -> None:
        from discord import app_commands

        @self.tree.command(name="kage", description="Talk to the supervisor")
        @app_commands.describe(message="Your message to Kage")
        async def _kage(interaction, message: str):  # type: ignore[no-untyped-def]
            await self._respond(interaction, str(interaction.user.id), message)

        @self.tree.command(name="kage-agents", description="List available agents")
        async def _agents(interaction):  # type: ignore[no-untyped-def]
            await self._respond(interaction, str(interaction.user.id), "agents")

        @self.tree.command(name="kage-memory", description="Remember a fact")
        @app_commands.describe(key="key", value="value")
        async def _memory(interaction, key: str, value: str):  # type: ignore[no-untyped-def]
            await self._respond(interaction, str(interaction.user.id),
                                f"memory add {key} {value}")

        @self.tree.command(name="kage-search", description="Web search (Whiz)")
        @app_commands.describe(query="what to search")
        async def _search(interaction, query: str):  # type: ignore[no-untyped-def]
            await self._respond(interaction, str(interaction.user.id), f"search {query}")

        @self.tree.command(name="kage-research", description="Deep research (Sage)")
        @app_commands.describe(query="topic")
        async def _research(interaction, query: str):  # type: ignore[no-untyped-def]
            await self._respond(interaction, str(interaction.user.id), f"research {query}")

        @self.tree.command(name="kage-session", description="Session control")
        @app_commands.describe(action="new | list | resume")
        async def _session(interaction, action: str = "new"):  # type: ignore[no-untyped-def]
            await self._respond(interaction, str(interaction.user.id), f"session {action}")

    # -- core routing --------------------------------------------------------
    async def _respond(self, interaction, user_id: str, text: str) -> None:  # type: ignore[no-untyped-def]
        resp = self.supervisor.think(text, user_id=user_id)
        self._apply_side_effects(resp.side_effects, user_id)
        reply = f"{resp.emoji_agent()} **{resp.agent}** · `{resp.intent}`\n{resp.text}"
        await interaction.response.send_message(reply[:1900])

    async def _on_message(self, message) -> None:  # type: ignore[no-untyped-def]
        import discord
        if message.author.bot:
            return
        is_dm = isinstance(message.channel, discord.DMChannel)
        mentioned = self.bot.user in message.mentions

        content = message.clean_content
        target_agent = None
        for mention in message.mentions:
            name = mention.name.lower()
            if mention != self.bot.user and name in self.supervisor.registry.list():
                target_agent = name
                content = content.replace(f"@{mention.name}", "").strip()
                break

        if not is_dm and not mentioned and not target_agent:
            if not any(w.lower() in content.lower()
                       for w in self.supervisor.registry.list()):
                return

        resp = self.supervisor.think(content, user_id=str(message.author.id),
                                     target_agent=target_agent)
        self._apply_side_effects(resp.side_effects, str(message.author.id))
        await message.channel.send(f"{resp.text}"[:1900])

    def _apply_side_effects(self, effects, user_id: str) -> None:  # type: ignore[no-untyped-def]
        for fx in effects or []:
            # memory/session are already applied by the supervisor; relay posts
            # out to a same-named channel best-effort.
            if fx.get("type") == "relay" and fx.get("channel"):
                self._relay(fx["channel"], fx.get("message", ""))

    def _relay(self, channel_name: str, text: str) -> None:
        import asyncio

        async def _do() -> None:
            import discord
            for guild in self.bot.guilds:
                ch = discord.utils.get(guild.text_channels, name=channel_name)
                if ch:
                    await ch.send(text[:1900])
                    return

        try:
            asyncio.create_task(_do())
        except RuntimeError:
            pass  # no running loop yet

    # -- lifecycle -----------------------------------------------------------
    def execute(self, task: Dict[str, Any] | None = None) -> Dict[str, Any]:
        import asyncio
        asyncio.run(self.bot.start(self.token))
        return {"ok": True}

    def sleep(self) -> None:
        import asyncio
        try:
            asyncio.run(self.bot.close())
        except Exception:  # noqa: BLE001
            pass
        self._awake = False


def _env(key: str) -> str:
    import os
    return os.environ.get(key, "")


# Augment Response with a helper for the agent emoji. Done at import to avoid
# a circular import with the supervisor module.
def _patch_response_emoji() -> None:
    from ...core.supervisor import Response
    if getattr(Response, "_emoji_patched", False):
        return

    def emoji_agent(self):  # type: ignore[no-untyped-def]
        return {"Kage": "🥷", "Mira": "🧠", "Whiz": "🌐", "Sage": "🔬",
                "Sentinel": "🛡️"}.get(self.agent, "🤖")

    Response.emoji_agent = emoji_agent  # type: ignore[attr-defined]
    Response._emoji_patched = True  # type: ignore[attr-defined]


_patch_response_emoji()
