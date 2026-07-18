#!/usr/bin/env python3
"""
KAGE OS CLI entry point.
"""

import os
import sys
import subprocess
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env (project root) before anything else.
load_dotenv(Path(__file__).resolve().parent / ".env")


def main():
    if len(sys.argv) < 2:
        print("Usage: python kage_cli.py [start|stop|status]")
        sys.exit(1)
    cmd = sys.argv[1]
    bot_path = str(Path(__file__).resolve().parent / "agents" / "telegram" / "bot_runner.py")
    if cmd == "start":
        print("Starting KAGE OS bot...")
        subprocess.run([sys.executable, bot_path])
    elif cmd == "stop":
        # Simple kill (assumes only one bot running)
        os.system("pkill -f bot_runner.py")
        print("Stopped KAGE OS bot.")
    elif cmd == "status":
        result = subprocess.run(["pgrep", "-f", "bot_runner.py"], capture_output=True)
        if result.returncode == 0:
            print("✅ KAGE OS bot is running (PID: {})".format(result.stdout.decode().strip()))
        else:
            print("❌ KAGE OS bot is not running.")
    else:
        print("Unknown command. Use: start, stop, status")
        sys.exit(1)


if __name__ == "__main__":
    main()
