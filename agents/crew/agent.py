#!/usr/bin/env python3
"""
Crew Agent — Multi-Agent Crew Orchestration for KAGE OS.
Inspired by https://github.com/crewAIInc/crewAI
Actions: run_crew, list_templates
"""

import gc
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple


class Agent:
    def __init__(self, context):
        self.context = context
        self.alive = False

    def wake(self, task_data: dict) -> dict:
        self.alive = True
        try:
            return self.execute(task_data)
        finally:
            self.sleep()

    def execute(self, task_data: dict) -> dict:
        action = task_data.get("action", "run_crew")
        crew_agents = task_data.get("agents", [])
        tasks = task_data.get("tasks", [])
        template_name = task_data.get("template", "")

        try:
            if action == "list_templates":
                return {
                    "status": "done",
                    "output": [
                        {
                            "name": "research_writer",
                            "description": "Researcher agent searches topic, Writer agent formats concise report",
                            "roles": ["Researcher", "Writer"]
                        },
                        {
                            "name": "coder_reviewer",
                            "description": "Developer agent generates solution, Code Reviewer validates code",
                            "roles": ["Developer", "Reviewer"]
                        },
                        {
                            "name": "web_note_saver",
                            "description": "Browser agent searches web, Trilium agent saves organized summary",
                            "roles": ["Web Scraper", "Note Archivist"]
                        }
                    ]
                }

            elif action == "run_crew":
                if template_name:
                    crew_agents, tasks = self._get_template(template_name, task_data.get("topic", "KAGE OS"))

                if not crew_agents or not tasks:
                    crew_agents = [
                        {"role": "Researcher", "goal": "Find key information on topic"},
                        {"role": "Summarizer", "goal": "Create crisp summary"}
                    ]
                    topic = task_data.get("topic", "AI Agents")
                    tasks = [
                        {"description": f"Gather details on {topic}", "agent": "Researcher"},
                        {"description": "Format summary into clear points", "agent": "Summarizer"}
                    ]

                results = self._orchestrate_crew(crew_agents, tasks)
                return {"status": "done", "output": results}

            else:
                return {"status": "error", "output": f"Unknown action: {action}"}

        except Exception as e:
            return {"status": "error", "output": str(e)}

    def _orchestrate_crew(self, crew_agents: List[Dict], tasks: List[Dict]) -> Dict:
        """Executes sequential multi-role crew workflow using Kage brain."""
        outputs = []
        context_accumulator = ""

        for idx, task in enumerate(tasks, start=1):
            role_name = task.get("agent", "Agent")
            role_info = next((a for a in crew_agents if a.get("role") == role_name), {"role": role_name})

            prompt = f"Role: {role_info.get('role')}\nGoal: {role_info.get('goal', '')}\nTask: {task.get('description')}"
            if context_accumulator:
                prompt += f"\n\nContext from previous crew steps:\n{context_accumulator}"

            brain_resp = self.context.brain.process_command("chat", {"message": prompt})
            step_output = brain_resp.get("response") or brain_resp.get("brain_response") or str(brain_resp)

            outputs.append({
                "step": idx,
                "role": role_name,
                "task": task.get("description"),
                "output": step_output
            })

            context_accumulator += f"\n--- Output from {role_name} ---\n{step_output}\n"

        return {
            "crew_status": "completed",
            "agent_count": len(crew_agents),
            "step_count": len(tasks),
            "final_output": context_accumulator.strip(),
            "step_details": outputs
        }

    def _get_template(self, name: str, topic: str) -> Tuple[List[Dict], List[Dict]]:
        if name == "research_writer":
            agents = [
                {"role": "Researcher", "goal": f"Gather research data on {topic}"},
                {"role": "Writer", "goal": "Draft clean markdown document"}
            ]
            tasks = [
                {"description": f"Identify top 3 facts about {topic}", "agent": "Researcher"},
                {"description": "Synthesize research facts into a executive summary", "agent": "Writer"}
            ]
            return agents, tasks
        elif name == "coder_reviewer":
            agents = [
                {"role": "Developer", "goal": f"Implement python script for {topic}"},
                {"role": "Reviewer", "goal": "Perform sanity check and unit test creation"}
            ]
            tasks = [
                {"description": f"Write Python code for {topic}", "agent": "Developer"},
                {"description": "Review code logic and write unit test snippet", "agent": "Reviewer"}
            ]
            return agents, tasks
        return [], []

    def sleep(self):
        self.alive = False
        gc.collect()
