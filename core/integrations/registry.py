#!/usr/bin/env python3
"""
registry.py — Central Integration & Provider Registry for KAGE OS.
Handles dynamic registration, lookup, health tracking, and instantiation of integrations.
"""

import logging
from typing import Dict, List, Optional, Type, Any
from .base import AbstractBaseIntegration, HealthStatus

logger = logging.getLogger("kage.registry")


class ProviderRegistry:
    """Central registry mapping provider keys to integration classes and live instances."""

    _registry: Dict[str, Type[AbstractBaseIntegration]] = {}
    _instances: Dict[str, AbstractBaseIntegration] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register integration classes by name."""
        def decorator(subclass: Type[AbstractBaseIntegration]):
            cls._registry[name.lower()] = subclass
            logger.info(f"Registered integration provider: {name.lower()}")
            return subclass
        return decorator

    @classmethod
    def register_class(cls, name: str, subclass: Type[AbstractBaseIntegration]):
        """Direct class registration method."""
        cls._registry[name.lower()] = subclass
        logger.info(f"Registered integration provider class: {name.lower()}")

    @classmethod
    def get_provider_class(cls, name: str) -> Optional[Type[AbstractBaseIntegration]]:
        """Retrieve integration class by name."""
        return cls._registry.get(name.lower())

    @classmethod
    def get_instance(cls, name: str, config: Optional[Dict[str, Any]] = None) -> Optional[AbstractBaseIntegration]:
        """Get or initialize live singleton instance of an integration."""
        key = name.lower()
        if key in cls._instances:
            inst = cls._instances[key]
            if config:
                inst.config.update(config)
            return inst

        provider_cls = cls.get_provider_class(key)
        if not provider_cls:
            logger.error(f"Provider '{name}' not found in ProviderRegistry")
            return None

        inst = provider_cls(name=key, config=config)
        inst.initialize()
        cls._instances[key] = inst
        return inst

    @classmethod
    def list_registered_providers(cls) -> List[str]:
        """List all registered provider names."""
        return sorted(list(cls._registry.keys()))

    @classmethod
    def health_check_all(cls) -> Dict[str, Dict[str, Any]]:
        """Run health checks across all initialized integration instances."""
        results = {}
        for name, instance in cls._instances.items():
            try:
                status = instance.health_check()
                results[name] = status.to_dict()
            except Exception as e:
                results[name] = HealthStatus(is_healthy=False, message=str(e)).to_dict()
        return results

    @classmethod
    def shutdown_all(cls):
        """Shutdown all active integration connections."""
        for name, instance in list(cls._instances.items()):
            try:
                instance.shutdown()
            except Exception as e:
                logger.error(f"Error during shutdown of '{name}': {e}")
        cls._instances.clear()
