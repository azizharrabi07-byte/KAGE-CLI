# KAGE OS — Migration Guide

## Upgrading from v1.x to v2.1

### 1. Unified Integration Architecture
In v1.x, external integrations were isolated. In v2.1, all integrations inherit from `AbstractBaseIntegration` and register in `ProviderRegistry`.
- Custom integration developers should extend `AbstractBaseIntegration` (`core/integrations/base.py`).

### 2. Built-in Core OS Features
`browser`, `openhands`, `mcp`, and `crew` are now built-in features accessible via `self.context` on any agent.
- `self.context.browser.search(query)`
- `self.context.openhands.execute_cmd(cmd)`
- `self.context.mcp.call_tool(...)`
- `self.context.crew.run_crew(...)`

### 3. Config Directory Location
Configuration now resides primarily at `~/.kage/config.toml`, with local repository `config.toml` serving as a secondary default fallback.
