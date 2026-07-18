"""
agents/telegram/bot_runner.py
Telegram bot runner with session management, memory tools, and action execution.
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from core.brain import Brain, extract_single_action
from core.session_manager import (
    create_session,
    get_active_session,
    add_message,
    get_session_context,
    handle_session_command,
)
from core.memory import handle_memory_command
from core.long_memory import add_fact, search_facts
from actions.browser import browser_action

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
LLM_PROVIDER = os.getenv("KAGE_LLM_PROVIDER", "groq")
LLM_API_KEY = os.getenv("KAGE_LLM_API_KEY")
LLM_MODEL = os.getenv("KAGE_LLM_MODEL", None)

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not set in .env")
    sys.exit(1)

brain = Brain(provider=LLM_PROVIDER, api_key=LLM_API_KEY, model=LLM_MODEL)

# Telegram message length limit
TELEGRAM_MAX_CHARS = 4000


async def _send(update: Update, text: str) -> None:
    """Send text as Markdown, auto-falling back to plain text on parse errors.

    Memory/browser/LLM output frequently contains characters (`_`, `*`, `` ` ``,
    `[`, `]`) that Telegram's Markdown parser rejects. Without this guard the
    bot raises BadRequest and the user receives nothing.
    """
    if not text:
        return
    for chunk in [text[i:i + TELEGRAM_MAX_CHARS] for i in range(0, len(text), TELEGRAM_MAX_CHARS)]:
        try:
            await update.message.reply_text(chunk, parse_mode="Markdown")
        except Exception:
            try:
                await update.message.reply_text(chunk)
            except Exception:
                pass


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session_id = create_session(title="New conversation")
    await _send(
        update,
        f"👋 Welcome to **KAGE OS**!\nSession: `{session_id}`\n\n"
        f"Commands:\n/new — Start new session\n/resume <id> — Resume session\n"
        f"/list — List sessions\n/delete <id> — Delete session\n/info — Show active session info",
    )


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    title = " ".join(context.args) if context.args else None
    result = handle_session_command("new", title)
    await _send(update, result)


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _send(update, "❌ Usage: `/resume <session_id>`")
        return
    result = handle_session_command("resume", context.args[0])
    await _send(update, result)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = handle_session_command("list")
    await _send(update, result)


async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = handle_session_command("info")
    await _send(update, result)


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _send(update, "❌ Usage: `/delete <session_id>`")
        return
    result = handle_session_command("delete", context.args[0])
    await _send(update, result)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    chat_id = update.effective_chat.id
    session_id = get_active_session()
    if not session_id:
        session_id = create_session(title=f"Chat {chat_id}")
    add_message(session_id, "user", user_message)
    session_context = get_session_context(session_id, max_messages=10)
    try:
        raw_response = brain.think(user_message, session_context=session_context)
        cleaned_action = extract_single_action(raw_response)
        try:
            action = json.loads(cleaned_action)
        except json.JSONDecodeError:
            action = {"action": "reply", "message": cleaned_action}
    except Exception as e:
        action = {"action": "reply", "message": f"❌ Brain error: {str(e)}"}
    result = await execute_action(action, update, context)
    add_message(session_id, "assistant", result, action_type=action.get("action", "reply"))
    await _send(update, result)


async def execute_action(action: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    action_type = action.get("action", "reply").lower()
    if action_type == "reply":
        return action.get("message", "No message provided.")
    elif action_type == "browser":
        query = action.get("query")
        url = action.get("url")
        depth = action.get("depth", 1)
        try:
            return browser_action(query=query, url=url, depth=depth)
        except Exception as e:
            return f"❌ Browser error: {str(e)}"
    elif action_type == "memory":
        sub = action.get("sub_action", "read")
        return handle_memory_command(
            sub,
            content=action.get("content", ""),
            old=action.get("old", ""),
            new=action.get("new", ""),
            file=action.get("file", "memory"),
            section=action.get("section"),
            query=action.get("query", ""),
            key=action.get("key", ""),
            value=action.get("value", ""),
        )
    elif action_type == "core_memory":
        sub = action.get("sub_action", "read")
        return handle_memory_command(
            f"core_{sub}",
            key=action.get("key", ""),
            value=action.get("value", ""),
        )
    elif action_type == "session":
        sub = action.get("sub_action", "info")
        arg = action.get("session_id") or action.get("title")
        return handle_session_command(sub, arg)
    elif action_type == "fact":
        sub = action.get("sub_action", "search")
        if sub == "add":
            fact_id = add_fact(
                action.get("fact", ""),
                category=action.get("category", "general"),
                source=action.get("source", ""),
            )
            return f"✅ Fact stored (ID: {fact_id})"
        elif sub == "search":
            facts = search_facts(action.get("query", ""), limit=5)
            if not facts:
                return "No matching facts found."
            lines = ["📚 Facts:"]
            for f in facts:
                lines.append(f"- [{f['category']}] {f['fact']}")
            return "\n".join(lines)
        else:
            return f"❌ Unknown fact command: `{sub}`"
    else:
        return (
            f"❌ Unknown action: `{action_type}`. "
            "Available: reply, browser, memory, core_memory, session, fact."
        )


def main():
    from core.session_manager import init_db
    from core.long_memory import init_db as init_long_mem
    init_db()
    init_long_mem()
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("new", cmd_new))
    application.add_handler(CommandHandler("resume", cmd_resume))
    application.add_handler(CommandHandler("list", cmd_list))
    application.add_handler(CommandHandler("info", cmd_info))
    application.add_handler(CommandHandler("delete", cmd_delete))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 KAGE OS Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
