#!/usr/bin/env python3
"""
Unit tests for Workflows & Scheduler Engine.
"""

import unittest
from core import memory, workflows
import kage


class TestWorkflowsAndScheduler(unittest.TestCase):
    def setUp(self):
        memory.init_db()
        self.supervisor = kage.Kage()
        self.supervisor.init_context()
        self.engine = workflows.WorkflowEngine(supervisor=self.supervisor)

    def tearDown(self):
        if self.supervisor.scheduler:
            self.supervisor.scheduler.stop()

    def test_workflow_registration_and_run(self):
        steps = [
            {"target": "openhands", "action": "run_python", "params": {"code": "print('step1_ok')"}},
            {"target": "openhands", "action": "run_python", "params": {"code": "print('step2_ok')"}}
        ]
        wf_id = self.engine.register_workflow("pipeline_test", steps)
        self.assertIsInstance(wf_id, int)

        res = self.engine.run_workflow(wf_id)
        self.assertEqual(res["status"], "completed")
        self.assertEqual(len(res["step_results"]), 2)


if __name__ == "__main__":
    unittest.main()
