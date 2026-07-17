#!/usr/bin/env python3
import os, sys, subprocess, gc, time
from pathlib import Path

class Agent:
    def __init__(self, context):
        self.context = context
        self.process = None
        self.pid_file = Path.home() / ".kage" / "telegram.pid"

    def wake(self, task_data=None):
        if self.process and self.process.poll() is None:
            return {"status": "already_running"}

        # Start the bot runner as a subprocess
        runner = str(Path(__file__).parent / "bot_runner.py")
        self.process = subprocess.Popen(
            ["python3", runner],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        # Save PID
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.write_text(str(self.process.pid))
        return {"status": "started", "pid": self.process.pid}

    def execute(self, task_data):
        return {"status": "ok"}

    def sleep(self):
        if self.process:
            self.process.terminate()
            time.sleep(1)
            if self.process.poll() is None:
                self.process.kill()
            self.process = None
        if self.pid_file.exists():
            self.pid_file.unlink()
        gc.collect()
        return {"status": "stopped"}
