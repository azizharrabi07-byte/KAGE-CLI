"""core/registry.py — agent registry with lazy loading and lifecycle control.

Agents register themselves (or are discovered) and are only instantiated when
first needed (lazy loading), keeping memory/CPU low on constrained devices like
Termux. The supervisor asks the registry for an agent by name or by intent.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Dict, Iterable, List, Optional

from .base_agent import BaseAgent

log = logging.getLogger("kage.registry")


class AgentRegistry:
    """Holds agent *factories* and lazily instantiates/awakes them."""

    def __init__(self) -> None:
        # name -> (factory, cached_instance_or_None)
        self._factories: Dict[str, Any] = {}
        self._instances: Dict[str, BaseAgent] = {}

    # -- registration --------------------------------------------------------
    def register(self, agent_cls: type[BaseAgent], config: Optional[Dict[str, Any]] = None) -> None:
        """Register an agent class (lazily instantiated on first use)."""
        name = getattr(agent_cls, "name", None) or agent_cls.__name__
        config = config or {}

        def _factory(supervisor: Any = None) -> BaseAgent:
            return agent_cls(supervisor=supervisor, config=dict(config))

        self._factories[name] = _factory
        log.debug("registered agent %s", name)

    def register_instance(self, agent: BaseAgent) -> None:
        """Register an already-constructed agent (skips lazy creation)."""
        self._instances[agent.name] = agent
        self._factories[agent.name] = lambda supervisor=None: agent
        log.debug("registered agent instance %s", agent.name)

    # -- discovery -----------------------------------------------------------
    def discover(self, dotted_paths: Iterable[str]) -> None:
        """Import modules and register any ``BaseAgent`` subclasses found.

        Each path is ``"package.module:AgentClass"`` or ``"package.module"``
        (registers all BaseAgent subclasses whose ``__module__`` matches).
        """
        for path in dotted_paths:
            try:
                if ":" in path:
                    mod_path, cls_name = path.split(":", 1)
                    module = importlib.import_module(mod_path)
                    cls = getattr(module, cls_name)
                    self.register(cls)
                else:
                    module = importlib.import_module(path)
                    for attr in vars(module).values():
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseAgent)
                            and attr is not BaseAgent
                            and getattr(attr, "__module__", "") == path
                        ):
                            self.register(attr)
            except Exception as exc:  # noqa: BLE001 — discovery must not crash boot
                log.warning("agent discovery failed for %s: %s", path, exc)

    # -- access --------------------------------------------------------------
    def get(self, name: str, supervisor: Any = None) -> Optional[BaseAgent]:
        """Return (lazily instantiating) an agent by name, or None."""
        if name in self._instances:
            return self._instances[name]
        factory = self._factories.get(name)
        if not factory:
            return None
        agent = factory(supervisor)
        self._instances[name] = agent
        return agent

    def list(self) -> List[str]:
        return sorted(self._factories)

    def all_info(self) -> List[Dict[str, Any]]:
        infos: List[Dict[str, Any]] = []
        for name in self.list():
            agent = self._instances.get(name) or self._factories[name](None)
            infos.append(agent.info())
        return infos

    # -- lifecycle -----------------------------------------------------------
    def wake(self, name: str, supervisor: Any = None) -> BaseAgent:
        agent = self.get(name, supervisor)
        if agent is None:
            raise KeyError(f"unknown agent: {name}")
        if not agent.is_awake:
            agent.wake()
        return agent

    def sleep(self, name: str) -> None:
        agent = self._instances.get(name)
        if agent and agent.is_awake:
            agent.sleep()

    def wake_all(self, supervisor: Any = None) -> int:
        count = 0
        for name in self.list():
            try:
                self.wake(name, supervisor)
                count += 1
            except Exception as exc:  # noqa: BLE001
                log.warning("failed to wake %s: %s", name, exc)
        return count

    def find_for_keyword(self, keyword: str) -> Optional[str]:
        """Return the name of an agent whose keywords include ``keyword``."""
        kw = keyword.lower()
        for info in self.all_info():
            if kw in [k.lower() for k in info["keywords"]]:
                return info["name"]
        return None
