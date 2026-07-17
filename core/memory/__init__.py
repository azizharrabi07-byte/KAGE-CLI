"""
KAGE OS Core Memory Package.
Exposes multi-type memory items, vector similarity search, persistence, facade manager,
and legacy kage.db helpers for trace/workflow logging.
"""

from .base import MemoryItem, MemoryType
from .store import MemoryStore
from .search import SemanticIndex
from .manager import MemoryManager
from .legacy import (
    init_db,
    log_trace,
    get_recent_traces,
    get_trace_by_id,
    create_workflow,
    get_workflow,
    get_pending_workflows,
    update_workflow_status,
    add_schedule,
    get_schedules,
    update_schedule_run,
    delete_schedule,
)

__all__ = [
    "MemoryItem",
    "MemoryType",
    "MemoryStore",
    "SemanticIndex",
    "MemoryManager",
    "init_db",
    "log_trace",
    "get_recent_traces",
    "get_trace_by_id",
    "create_workflow",
    "get_workflow",
    "get_pending_workflows",
    "update_workflow_status",
    "add_schedule",
    "get_schedules",
    "update_schedule_run",
    "delete_schedule",
]
