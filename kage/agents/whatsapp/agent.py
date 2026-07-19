"""agents/whatsapp/agent.py — WhatsApp bridge agent."""

from __future__ import annotations
from typing import Any, Dict

from ...core.base_agent import BaseAgent
from ...core.integrations.whatsapp import WhatsAppIntegration


class WhatsAppAgent(BaseAgent):
    name = "whatsapp"
    kind = "whatsapp"
    description = "Bridges WhatsApp messages to/from Kage via a local bridge."
    emoji = "💬"

    def wake(self) -> None:
        self.integration = WhatsAppIntegration(config=self.config, timeout=15.0)
        self._awake = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        op = str(task.get("op", task.get("action", "status")))
        if op in ("status", "whatsapp.status"):
            return self.integration.health_check().to_dict()
        if op in ("qr", "whatsapp.qr"):
            return {"status": "ok", "data": self._call(self.integration.request_qr), "error": None}
        if op in ("restore", "whatsapp.restore"):
            return {"status": "ok", "data": self._call(self.integration.restore_session), "error": None}
        if op in ("send", "whatsapp.send"):
            res = self.integration.send({"to": task.get("to", ""), "text": task.get("text", "")})
            return res.to_dict()
        if op in ("receive", "whatsapp.receive", "poll"):
            res = self.integration.receive()
            return res.to_dict()
        return {"status": "error", "data": None, "error": f"unknown whatsapp op: {op}"}

    @staticmethod
    def _call(fn):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}

    def sleep(self) -> None:
        if hasattr(self, "integration"):
            self.integration.disconnect()
        self._awake = False
