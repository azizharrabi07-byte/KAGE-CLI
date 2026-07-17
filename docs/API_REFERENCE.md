# KAGE OS — API Reference

## 1. Integrations API (`core/integrations/`)

### `ProviderRegistry`
* `ProviderRegistry.register(name: str)`: Decorator to register integration class.
* `ProviderRegistry.get_instance(name: str, config: dict)`: Retrieve active integration instance.
* `ProviderRegistry.health_check_all()`: Run health checks on all initialized providers.

### `AbstractBaseIntegration`
* `initialize() -> bool`: Setup network sessions and credentials.
* `health_check() -> HealthStatus`: Query provider health metrics.
* `execute(action: str, params: dict) -> dict`: Perform provider action.
* `shutdown() -> bool`: Cleanly release active resources.

---

## 2. Tools API (`core/tools/`)

### `ToolRegistry`
* `ToolRegistry.register(tool: BaseTool)`: Register system tool.
* `ToolRegistry.execute_tool(name: str, args: dict, context)`: Execute tool with schema validation and security checks.

---

## 3. Memory API (`core/memory/`)

### `MemoryManager`
* `add_memory(content: str, user_id: str, memory_type: MemoryType, importance: float)`: Save memory.
* `search_memories(query: str, user_id: str, top_k: int) -> list`: Perform vector similarity search.
* `cleanup() -> int`: Remove expired TTL items.
