from __future__ import annotations

import asyncio

import pytest

from llm_api.background_tasks import BackgroundTaskRegistry


class TestBackgroundTaskRegistry:
    @pytest.mark.asyncio
    async def test_shutdown_cancels_tracked_tasks(self):
        registry = BackgroundTaskRegistry()
        cancelled = asyncio.Event()

        async def worker():
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                cancelled.set()
                raise

        registry.create_task(worker(), name="test-worker")
        await asyncio.sleep(0)
        remaining = await registry.shutdown(timeout=0.5)

        assert remaining == 0
        assert cancelled.is_set()

    @pytest.mark.asyncio
    async def test_shutdown_returns_zero_when_no_tasks(self):
        registry = BackgroundTaskRegistry()
        remaining = await registry.shutdown(timeout=0.1)
        assert remaining == 0
