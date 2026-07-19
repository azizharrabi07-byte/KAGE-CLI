"""agents/telegram/agent.py — OPTIONAL / DEPRECATED transport.

Telegram remains for backward compatibility. Discord is the primary interface.
Enable with:  kage start --use-telegram   (requires python-telegram-bot).

Implements the same wake/execute/sleep lifecycle and routes through the
supervisor, so behavior is identical to Discord.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ...core.base_agent import BaseAgent

log = logging.getLogger("kage.telegram")


class TelegramAgent(BaseAgent):
    name = "telegram"
    kind = "telegram"
    description = "Optional/deprecated Telegram interface."
    emoji = "✈️"

    def wake(self) -> None:
        try:
            from telegram.ext import ApplicationBuilder
        except ImportError as exc:
            raise RuntimeError("python-telegram-bot not installed") from exc
        token = self.config.get("token") or _env("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required for the Telegram agent")
        self.application = ApplicationBuilder().token(token).build()
        self._register_handlers()
        self._awake = True

    def _register_handlers(self) -> None:
        from telegram.ext import CommandHandler, MessageHandler, filters

        async def on_message(update, context):  # type: ignore[no-untyped-def]
            if not update.message or not update.message.text:
                return
            uid = str(update.effective_user.id)
            resp = self.supervisor.think(update.message.text, user_id=uid)
            await update.message.reply_text(resp.text[:4000])

        self.application.add_handler(CommandHandler("kage", on_message))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    def execute(self, task: Dict[str, Any] | None = None) -> Dict[str, Any]:
        import asyncio

        async def _run() -> None:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            await asyncio.Event().wait()  # run until stopped

        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            pass
        return {"ok": True}

    def sleep(self) -> None:
        import asyncio

        async def _stop() -> None:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

        try:
            asyncio.run(_stop())
        except Exception:  # noqa: BLE001
            pass
        self._awake = False


def _env(key: str) -> str:
    import os
    return os.environ.get(key, "")
