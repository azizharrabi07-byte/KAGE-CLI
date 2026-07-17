# KAGE OS — Code & Prompt Examples

## 1. Natural Language Web Search & Synthesis
```bash
kage chat "Search the web for OpenHands AI framework and summarize key features"
```

## 2. Dynamic Provider Switching
```bash
# Switch to Groq provider with Llama 3.3 model
kage chat "/config set llm.provider groq"
kage chat "/config set llm.model llama-3.3-70b-versatile"
```

## 3. Creating Notes in Obsidian
```bash
kage chat "Create a note in Obsidian titled Standup.md with content Sprint roadmap finalized"
```

## 4. Running Multi-Step Workflows via Python API
```python
from core.workflows import WorkflowEngine
import kage

sup = kage.Kage()
sup.init_context()
engine = WorkflowEngine(supervisor=sup)

steps = [
    {"target": "browser", "action": "search", "params": {"query": "OpenHands AI"}},
    {"target": "openhands", "action": "write_code", "params": {"path": "summary.txt", "content": "{{step_1.output}}"}}
]

wf_id = engine.register_workflow("search_and_save", steps)
result = engine.run_workflow(wf_id)
print(result)
```
