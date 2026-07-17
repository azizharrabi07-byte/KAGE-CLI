# KAGE OS Changelog

All notable changes to the KAGE OS project will be documented in this file.

## [2.1.0] - 2026-07-18

### Added
- **Unified Integration Layer (`core/integrations/`)**: Abstract Base Integration contract, Provider Registry, Plugin Loader, Exponential Backoff Retry Engine, and Sliding Window Rate Limiter.
- **7 Integration Providers**: `GeminiProvider`, `GroqProvider`, `OpenRouterProvider`, `OllamaProvider`, `ObsidianProvider`, `WhatsAppProvider`, `TelegramProvider`.
- **Modular Prompt Architecture (`core/prompts/`)**: 12 standard prompt blueprints, PromptVersionRegistry, PromptCompressor, and ContextBuilder.
- **Extensible Agent Framework (`core/agents/`)**: BaseAgent class contract, 7 specialized agent sub-types, AgentRunner ThreadPoolExecutor, and AgentMetrics.
- **Production CLI Engine (`core/cli/`)**: Readline Tab Autocompletion, Table & Output Formatters (JSON/YAML), Config Setup Wizard, and Execution Flags (`--dry-run`, `--debug`, `--verbose`).
- **Advanced Multi-Type Memory Engine (`core/memory/`)**: 5 Memory Types (`CONVERSATION`, `KNOWLEDGE`, `WORKING`, `EPISODIC`, `SEMANTIC`), Pure-Python TF-IDF Vector Cosine Similarity Search Index, Importance Scoring (1-10), and TTL Expiration.
- **Standardized Tool Framework (`core/tools/`)**: BaseTool, ToolMetadata, PermissionLevels (`SAFE`, `SENSITIVE`, `CRITICAL`), and implementations for Bash, Python, File, Web, and Memory operations.
- **Hardened Security Framework (`core/security/`)**: SafePathValidator preventing directory traversal attacks, InputSanitizer, SecretRedactor automated credential masking, and SecurityManager authorization policies.
- **Multi-Step Workflow Engine (`core/workflows.py`)**: Persistent multi-step execution state machine with handlebars output variable substitution.
- **Telegram Bot Integration (`@Mini_kage_bot`)**: Native long-polling worker daemon, auto-spawned by Kage supervisor, with per-user persistent context memory (`~/.kage/memory.json`).
- **Complete Technical Documentation Set (`docs/`)**: Architecture, Developer, Plugin, Agent, Prompt, API, Configuration, Examples, Troubleshooting, Contributing, Roadmap, and Migration Guides.
- **GitHub Actions CI/CD Pipeline (`.github/workflows/ci.yml`)**: Multi-version Python syntax verification and test automation workflows.

### Fixed
- Fixed shell injection risks by introducing parameterized list-based execution in tool wrappers.
- Fixed directory traversal vulnerabilities with workspace boundary checks in path validator.
- Fixed 429 quota rate limit crashes with model failover sequences (`gemini-2.5-flash` -> `gemini-2.0-flash` -> `gemini-2.0-flash-lite`).
- Standardized CLI process exit codes (0 for success, 1 for error).
