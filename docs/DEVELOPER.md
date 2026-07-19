# Developer guide

## Add a new agent
Implement `kage.core.base_agent.BaseAgent` (set `name`/`kind`, implement
`wake`/`execute`/`sleep`) and register it in the `AgentRegistry`.

## Add a new tool/action
Add a case to the tool registry returning a `ToolResult` envelope:
```python
from kage.core.result import ToolResult
def my_tool(x: str) -> ToolResult:
    return ToolResult.success({"echo": x})
```
The supervisor handles permission gating (`core/security.py`) automatically.

## Return contract
Every tool/integration returns:
```python
ToolResult(status="ok"|"error", data=<any>|None, error=str|None,
           durationMs=float, attempts=int, meta=dict)
```

## Run the new Phase 3-8 tests
```bash
python kage/tests/test_phases_3_8.py
```

## Secrets
Read secrets via `kage.core.secrets.resolve("KEY")` (env only). Never log raw
values — `observability.log_event` scrubs known secret patterns automatically.
