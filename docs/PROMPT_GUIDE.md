# KAGE OS — Prompt Guide

## Overview

All system and operational prompts live in the modular prompt framework under `core/prompts/`. Prompts are defined as version-controlled `PromptTemplate` objects registered in `PromptVersionRegistry`.

## Standard Prompt Templates

1. `SystemPrompt`: Main system instructions listing features and action JSON schemas.
2. `DeveloperPrompt`: Software architecture and low-level Python coding instructions.
3. `ToolPrompt`: Parameter validation and JSON tool response schema definitions.
4. `PlannerPrompt`: Step-by-step task decomposition blueprint instructions.
5. `ReasoningPrompt`: Chain-of-thought analysis guidelines.
6. `MemoryPrompt`: Fact extraction and persistent user attribute identification.
7. `SummarizerPrompt`: Executive summary condensation guidelines.
8. `AgentPrompt`: Specialized domain role execution rules.
9. `ReflectionPrompt`: Post-execution critique and validation analysis.
10. `ExecutionPrompt`: Direct sandbox execution instructions.
11. `SafetyPrompt`: Boundary checks and permission level evaluations.
12. `ErrorRecoveryPrompt`: Self-healing exception analysis and failover strategy generation.

## Example Rendering

```python
from core.prompts import PromptVersionRegistry

template = PromptVersionRegistry.get("planner", "v1.0")
rendered_prompt = template.render(goal="Deploy OS", constraints="Low power mode")
```
