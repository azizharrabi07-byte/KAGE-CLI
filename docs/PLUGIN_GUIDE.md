# KAGE OS — Plugin Guide

## Overview

KAGE OS supports dynamic third-party plugins loaded from `~/.kage/plugins` and `plugins/`. Plugins can register custom integrations, custom tool wrappers, and specialized agents at runtime.

## Creating a Plugin

Place a Python file (e.g. `my_plugin.py`) in `~/.kage/plugins/`:

```python
from core.integrations import AbstractBaseIntegration, ProviderRegistry, HealthStatus

@ProviderRegistry.register("my_service")
class MyCustomService(AbstractBaseIntegration):
    def validate_config(self) -> bool:
        return True

    def initialize(self) -> bool:
        self.is_initialized = True
        return True

    def health_check(self) -> HealthStatus:
        return HealthStatus(is_healthy=True, message="Custom service OK")

    def execute(self, action: str, params: dict) -> dict:
        return {"status": "done", "output": f"Executed {action}"}

    def shutdown(self) -> bool:
        return True

def register_plugin(registry):
    """Optional hook called by PluginLoader on startup."""
    print("My custom plugin registered successfully!")
```
