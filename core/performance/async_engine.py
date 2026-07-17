#!/usr/bin/env python3
"""
async_engine.py — Non-Blocking Async I/O Engine for KAGE OS.
Provides asyncio task pools and non-blocking coroutine dispatch wrappers.
Part of Phase 10 Performance Optimization.
"""

import asyncio
import logging
import concurrent.futures
from typing import Dict, List, Optional, Any, Callable, Coroutine

logger = logging.getLogger("kage.performance.async")


class AsyncEngine:
    """Async I/O manager coordinating non-blocking tasks using asyncio event loops."""

    _loop: Optional[asyncio.AbstractEventLoop] = None
    _executor: Optional[concurrent.futures.ThreadPoolExecutor] = None

    @classmethod
    def get_event_loop(cls) -> asyncio.AbstractEventLoop:
        """Get or create shared asyncio event loop."""
        if cls._loop is None or cls._loop.is_closed():
            try:
                cls._loop = asyncio.get_running_loop()
            except RuntimeError:
                cls._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(cls._loop)
        return cls._loop

    @classmethod
    def run_coroutine(cls, coro: Coroutine[Any, Any, Any]) -> Any:
        """Run coroutine synchronously on shared event loop."""
        loop = cls.get_event_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=60.0)
        else:
            return loop.run_until_complete(coro)

    @classmethod
    async def run_in_executor(cls, func: Callable, *args, **kwargs) -> Any:
        """Execute blocking synchronous function inside non-blocking thread executor."""
        loop = cls.get_event_loop()
        if cls._executor is None:
            cls._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=10, thread_name_prefix="KageAsyncExecutor"
            )
        pfunc = lambda: func(*args, **kwargs)
        return await loop.run_in_executor(cls._executor, pfunc)
