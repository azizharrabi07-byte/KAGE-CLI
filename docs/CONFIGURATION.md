# KAGE OS — Configuration Guide

## Configuration Locations

KAGE OS reads configuration dynamically from:
1. Primary User Config: `~/.kage/config.toml`
2. Local Repository Config: `./config.toml`

Values in `~/.kage/config.toml` override default repository configuration parameters.

## TOML Specification Example

```toml
[llm]
provider = "gemini"                      # gemini | groq | openrouter | ollama
api_key = "AQ.Ab8RN6..."                 # LLM API key
model = "gemini-2.5-flash"               # Model name
base_url = "https://generativelanguage.googleapis.com/v1beta"

[obsidian]
url = "http://localhost:27123"           # Local REST API URL
api_key = "4224414d3d95d207e105..."       # Bearer token
vault = "KAGE"                           # Vault name

[telegram]
bot_token = "8819096503:AAEqOGM_..."     # Telegram bot token

[whatsapp]
test_number = "1234567890"               # Target test phone number

[mcp]
servers = [
    { name = "fetch", url = "http://localhost:8000/mcp" },
    { name = "filesystem", url = "http://localhost:8001/mcp" }
]

[system]
log_level = "info"                       # debug | info | warning | error
max_retries = 3
timeout = 30
```
