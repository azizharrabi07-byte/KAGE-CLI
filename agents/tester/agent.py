#!/usr/bin/env python3
"""Agent: tester"""

import gc
import sys
from typing import Dict


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False

    def wake(self, task_data: dict) -> dict:
        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        # Implement your logic here
        return {"status": "done", "output": "Not implemented yet"}

    def sleep(self):
        self.alive = False
        gc.collect()
