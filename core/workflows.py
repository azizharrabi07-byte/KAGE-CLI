#!/usr/bin/env python3
"""
workflows.py — Workflow Execution Engine for KAGE OS.
Supports creation, persistence, multi-step execution, and state tracking for multi-agent workflows.
Completes Phase 2 feature requirement.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from core.memory import (
    create_workflow,
    get_workflow,
    get_pending_workflows,
    update_workflow_status,
)

logger = logging.getLogger("kage.workflows")


class WorkflowEngine:
    """Executes multi-step structured workflows and tracks state in kage.db."""

    def __init__(self, supervisor=None):
        self.supervisor = supervisor

    def register_workflow(self, name: str, steps: List[Dict[str, Any]]) -> int:
        """Create a new workflow record in memory database."""
        if not steps or not isinstance(steps, list):
            raise ValueError("Steps must be a non-empty list of step dictionaries")
        wf_id = create_workflow(name, steps)
        logger.info(f"Created workflow '{name}' with ID {wf_id}")
        return wf_id

    def run_workflow(self, workflow_id: int) -> Dict[str, Any]:
        """Execute all steps in a persisted workflow sequentially."""
        wf = get_workflow(workflow_id)
        if not wf:
            return {"status": "error", "message": f"Workflow {workflow_id} not found"}

        update_workflow_status(workflow_id, "running")
        steps = json.loads(wf["steps_json"]) if isinstance(wf["steps_json"], str) else wf["steps_json"]

        results = []
        context_data = {}

        for idx, step in enumerate(steps, start=1):
            agent_or_feature = step.get("target") or step.get("agent") or step.get("feature")
            action = step.get("action", "")
            payload = step.get("params") or step.get("task") or {}

            interpolated_payload = self._interpolate_payload(payload, context_data)

            start_t = time.time()
            step_result = {}

            try:
                if self.supervisor:
                    step_result = self.supervisor._execute_action_payload(
                        action_type=agent_or_feature,
                        task_data=interpolated_payload
                    )
                else:
                    step_result = {"status": "error", "message": "Supervisor instance unavailable"}

                duration_ms = (time.time() - start_t) * 1000
                results.append({
                    "step": idx,
                    "target": agent_or_feature,
                    "action": action,
                    "duration_ms": round(duration_ms, 2),
                    "result": step_result
                })

                if step_result.get("status") == "error":
                    update_workflow_status(workflow_id, "failed")
                    return {
                        "status": "failed",
                        "workflow_id": workflow_id,
                        "failed_step": idx,
                        "step_results": results
                    }

                context_data[f"step_{idx}"] = step_result.get("output", step_result)

            except Exception as e:
                update_workflow_status(workflow_id, "failed")
                logger.error(f"Workflow {workflow_id} failed on step {idx}: {e}")
                return {
                    "status": "failed",
                    "workflow_id": workflow_id,
                    "error": str(e),
                    "step_results": results
                }

        update_workflow_status(workflow_id, "completed")
        return {
            "status": "completed",
            "workflow_id": workflow_id,
            "total_steps": len(steps),
            "step_results": results
        }

    def process_pending_workflows(self) -> List[Dict[str, Any]]:
        """Resume execution for any pending workflows in database."""
        pending = get_pending_workflows()
        res = []
        for wf in pending:
            out = self.run_workflow(wf["id"])
            res.append(out)
        return res

    @staticmethod
    def _interpolate_payload(payload: Dict, context: Dict) -> Dict:
        """Substitute string placeholders in step payload from previous context."""
        raw_str = json.dumps(payload)
        for k, v in context.items():
            val_str = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            raw_str = raw_str.replace(f"{{{{{k}}}}}", val_str.strip('"'))
        try:
            return json.loads(raw_str)
        except Exception:
            return payload
