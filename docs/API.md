# API reference (Phases 3-8)

## CLI (`kage cli` / `python -m kage.cli`)
Flags: `--json`, `--yaml`, `--dry-run`. No args → interactive REPL.
```
/help  /agents  /models  /providers  /version
/config list | get <k> | set <k> <v>
/secrets list | add <k> <v> | remove <k>
/workflows        run the branching demo
/shell <command>  validate/exec in the sandbox
/health           exercise retry/timeout backoff
/exit
```

## Python modules
| Module | Key symbols |
|---|---|
| `kage.core.result` | `ToolResult.success/failure`, `timed` |
| `kage.core.health` | `run_with_retry(fn, *, max_attempts, base_delay, backoff_factor, timeout)`, `probe` |
| `kage.core.secrets` | `resolve`, `mask`, `scrub`, `list_secrets`, `add_secret`, `remove_secret` |
| `kage.core.observability` | `log_event`, `record_metric`, `metric_summary`, `add_trace`, `TraceSpan` |
| `kage.core.sandbox` | `sanitize`, `validate_command`, `run(command, *, dry_run, timeout)` |
| `kage.core.workflows.branching` | `Step`, `Branch`, `Retry`, `Workflow`, `execute_workflow` |

## ToolResult envelope
`{status, data, error, durationMs, attempts, meta}` — consistent across every
tool and integration, identical to the web control plane contract.
