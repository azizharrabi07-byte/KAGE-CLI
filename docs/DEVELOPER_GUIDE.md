# KAGE OS — Developer Guide

## Development Environment Setup

```bash
# 1. Clone & Setup
git clone https://github.com/azizharrabi07-byte/KAGE-CLI.git
cd KAGE-CLI
bash setup.sh

# 2. Run Test Suite
python3 -m unittest discover -s tests
```

## Adding a Custom Agent

To scaffold a new custom agent, use `kage_cli.py`:

```bash
kage agent create myagent
```

This generates `agents/myagent/agent.py` and registers it in `agents/registry.json`.

Example Custom Agent Class:

```python
from core.agents import BaseAgent

class CustomAgent(BaseAgent):
    def wake(self, task_data: dict) -> dict:
        return self.execute(task_data)

    def execute(self, task_data: dict) -> dict:
        action = task_data.get("action", "default")
        # Perform custom logic...
        return {"status": "done", "output": f"Processed action {action}"}
```

## Running Unit Tests

```bash
python3 -m unittest discover -s tests
```
