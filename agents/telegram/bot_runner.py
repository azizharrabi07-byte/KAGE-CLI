#!/usr/bin/env python3
import os, sys, json, subprocess, shlex, asyncio
from pathlib import Path

# Add Kage core to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.brain import brain
import toml

# Load config
config_path = Path(__file__).parent.parent.parent / "config.toml"
config = toml.load(config_path)
TOKEN = config.get("telegram", {}).get("bot_token")
if not TOKEN:
    print("No Telegram token found in config")
    sys.exit(1)

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Action executor (same as before) ---
def execute_action(action, task):
    if action == "system":
        return "✅ System action executed."
    elif action == "openhands":
        cmd = task.get("command") or task.get("action")
        if not cmd:
            return "❌ No command specified."
        try:
            result = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=30)
            output = result.stdout if result.returncode == 0 else result.stderr
            return f"✅ Command output:\n{output[:500]}" if output else "✅ Command executed."
        except Exception as e:
            return f"❌ Command failed: {e}"
    elif action == "crew":
        try:
            cmd = ["python3", "/data/data/com.termux/files/home/kage-os/kage_cli.py", "crew", "run", json.dumps(task)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = result.stdout if result.returncode == 0 else result.stderr
            return f"✅ Crew result:\n{output[:500]}" if output else "✅ Crew executed."
        except Exception as e:
            return f"❌ Crew error: {e}"
    else:
        return f"⚠️ Action '{action}' not supported yet."

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm Kage. Ask me anything.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    try:
        b = brain()
        reply = b.ask(text)
        # Check if reply is a JSON action
        if reply.strip().startswith("{") and "action" in reply:
            try:
                action_data = json.loads(reply)
                action_name = action_data.get("action")
                task = action_data.get("task", {})
                result = execute_action(action_name, task)
                await update.message.reply_text(result)
            except json.JSONDecodeError:
                await update.message.reply_text(reply)
        else:
            await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# --- Main ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("[TELEGRAM BOT] Starting polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
