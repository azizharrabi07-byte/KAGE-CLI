#!/usr/bin/env python3
"""
base.py — Abstract Base Integration & Execution Framework for KAGE-CLI.
Provides unified lifecycle management, health checks, automatic retries with exponential backoff,
rate limiting, configuration validation, and graceful failure recovery for all external services.
"""

import abc
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, TypeVar, Generic

T = TypeVar("T")

logger = logging.getLogger("kage.integrations")


@dataclass
class HealthStatus:
    """Standardized integration health status representation."""
    is_healthy: bool
    latency_ms: float = 0.0
    status_code: str = "UNKNOWN"
    message: str = ""
    last_check: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "healthy": self.is_healthy,
            "latency_ms": round(self.latency_ms, 2),
            "status_code": self.status_code,
            "message": self.message,
            "last_check": self.last_check,
        }


class RetryEngine:
    """Production-grade retry helper with exponential backoff and jitter."""

    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0, max_delay: float = 10.0, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def execute_with_retry(self, func: Callable[[], T], retryable_exceptions: tuple = (Exception,)) -> T:
        """Executes function with exponential backoff retries."""
        attempt = 0
        current_delay = self.initial_delay

        while True:
            try:
                return func()
            except retryable_exceptions as e:
                attempt += 1
                if attempt > self.max_retries:
                    logger.error(f"Execution failed after {self.max_retries} attempts: {e}")
                    raise e

                # Jitter calculation
                sleep_time = min(self.max_delay, current_delay * (1 + random.random() * 0.1))
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed ({e}). Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)
                current_delay *= self.backoff_factor


class RateLimiter:
    """Sliding-window rate limiter for external API calls."""

    def __init__(self, max_calls: int = 60, period_seconds: float = 60.0):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self.timestamps: List[float] = []

    def acquire(self) -> bool:
        """Enforces rate limit, sleeping if quota is temporarily exhausted."""
        now = time.time()
        # Remove timestamps outside window
        self.timestamps = [t for t in self.timestamps if now - t < self.period_seconds]

        if len(self.timestamps) >= self.max_calls:
            oldest = self.timestamps[0]
            sleep_needed = self.period_seconds - (now - oldest)
            if sleep_needed > 0:
                logger.warning(f"Rate limit hit ({self.max_calls} calls/{self.period_seconds}s). Pausing for {sleep_needed:.2f}s...")
                time.sleep(sleep_needed)
            self.timestamps.pop(0)

        self.timestamps.append(time.time())
        return True


class AbstractBaseIntegration(abc.ABC):
    """Unified Abstract Base Integration class for all external providers and services."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.is_initialized = False
        self.retry_engine = RetryEngine(
            max_retries=int(self.config.get("max_retries", 3)),
            initial_delay=float(self.config.get("initial_delay", 1.0)),
        )
        self.rate_limiter = RateLimiter(
            max_calls=int(self.config.get("max_calls_per_minute", 60)),
            period_seconds=60.0
        )
        self.last_health = HealthStatus(is_healthy=False, message="Uninitialized")

    @abc.abstractmethod
    def validate_config(self) -> bool:
        """Validate required configuration keys and structure."""
        pass

    @abc.abstractmethod
    def initialize(self) -> bool:
        """Initialize connection parameters, clients, and sessions."""
        pass

    @abc.abstractmethod
    def health_check(self) -> HealthStatus:
        """Perform active ping/status health check against external provider."""
        pass

    @abc.abstractmethod
    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute integration action with params."""
        pass

    @abc.abstractmethod
    def shutdown(self) -> bool:
        """Gracefully release network connections and workers."""
        pass

    def safe_execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action with rate limiting, retries, and unified exception handling."""
        if not self.is_initialized:
            self.initialize()

        self.rate_limiter.acquire()

        def _run():
            return self.execute(action, params)

        try:
            return self.retry_engine.execute_with_retry(_run)
        except Exception as e:
            logger.error(f"[{self.name}] Error executing action '{action}': {e}")
            return {
                "status": "error",
                "integration": self.name,
                "action": action,
                "error": str(e),
            }
