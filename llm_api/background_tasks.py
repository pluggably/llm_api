from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Coroutine, Optional, Set


logger = logging.getLogger(__name__)


@dataclass
class BackgroundTaskRegistry:
    """Tracks fire-and-forget asyncio tasks for coordinated shutdown."""

    _tasks: Set[asyncio.Task[Any]] = field(default_factory=set)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def create_task(
        self,
        coro: Coroutine[Any, Any, Any],
        *,
        name: Optional[str] = None,
    ) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro, name=name)
        with self._lock:
            self._tasks.add(task)
        task.add_done_callback(self._discard_task)
        return task

    def _discard_task(self, task: asyncio.Task[Any]) -> None:
        with self._lock:
            self._tasks.discard(task)

    async def shutdown(self, timeout: float) -> int:
        """Cancel tracked tasks and wait up to timeout seconds.

        Returns the number of tasks still unfinished after the timeout.
        """
        with self._lock:
            tasks = [task for task in self._tasks if not task.done()]

        if not tasks:
            return 0

        for task in tasks:
            task.cancel()

        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=max(0.0, timeout),
            )
        except asyncio.TimeoutError:
            pass

        pending = [task for task in tasks if not task.done()]
        if pending:
            logger.warning(
                "Shutdown timed out waiting for %d background task(s)",
                len(pending),
            )
        return len(pending)


_background_task_registry: Optional[BackgroundTaskRegistry] = None


def get_background_task_registry() -> BackgroundTaskRegistry:
    global _background_task_registry
    if _background_task_registry is None:
        _background_task_registry = BackgroundTaskRegistry()
    return _background_task_registry
