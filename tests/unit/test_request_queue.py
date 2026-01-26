"""Tests for request queue management."""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone

from llm_api.queue import RequestQueueManager, get_queue_manager


@pytest.fixture
def queue_manager():
    """Create a fresh queue manager for testing."""
    manager = RequestQueueManager()
    
    def mock_executor(request):
        # Simulate some processing time
        import time
        time.sleep(0.01)
        return {"result": f"processed-{request.request_id}"}
    
    manager.configure(executor=mock_executor)
    return manager


class TestRequestQueueManager:
    """Test suite for RequestQueueManager."""
    
    @pytest.mark.asyncio
    async def test_enqueue_request(self, queue_manager):
        """Test enqueueing a request."""
        request = await queue_manager.enqueue(
            model_id="test-model",
            modality="text",
            input_data={"prompt": "Hello"},
        )
        
        assert request.request_id is not None
        assert request.model_id == "test-model"
        assert request.status in ("queued", "running", "completed")
    
    @pytest.mark.asyncio
    async def test_wait_for_completion(self, queue_manager):
        """Test waiting for a request to complete."""
        request = await queue_manager.enqueue(
            model_id="test-model",
            modality="text",
            input_data={"prompt": "Hello"},
        )
        
        completed = await queue_manager.wait_for_completion(request, timeout=5.0)
        
        assert completed.status == "completed"
        assert completed.result is not None
    
    @pytest.mark.asyncio
    async def test_get_request(self, queue_manager):
        """Test retrieving a request by ID."""
        request = await queue_manager.enqueue(
            model_id="test-model",
            modality="text",
            input_data={"prompt": "Hello"},
        )
        
        retrieved = queue_manager.get_request(request.request_id)
        assert retrieved is not None
        assert retrieved.request_id == request.request_id
    
    @pytest.mark.asyncio
    async def test_cancel_queued_request(self, queue_manager, monkeypatch):
        """Test cancelling a queued request."""
        # Create a slow executor
        async def slow_executor(request):
            await asyncio.sleep(10)
            return {"result": "slow"}
        
        # Fill queue to force queueing
        requests = []
        for i in range(5):
            req = await queue_manager.enqueue(
                model_id="test-model",
                modality="text",
                input_data={"prompt": f"Request {i}"},
            )
            requests.append(req)
        
        # Try to cancel a queued one
        for req in requests:
            if req.status == "queued":
                cancelled = queue_manager.cancel_request(req.request_id)
                assert cancelled
                assert req.status == "cancelled"
                break
    
    @pytest.mark.asyncio
    async def test_queue_position(self, queue_manager):
        """Test queue position tracking."""
        # Enqueue multiple requests
        requests = []
        for i in range(3):
            req = await queue_manager.enqueue(
                model_id="test-model",
                modality="text",
                input_data={"prompt": f"Request {i}"},
            )
            requests.append(req)
        
        # Check that at least some show queue position
        positions = [
            queue_manager.get_queue_position(r.request_id)
            for r in requests
        ]
        # At least one should have been queued
        assert any(p is not None for p in positions) or all(
            r.status == "completed" for r in requests
        )
    
    @pytest.mark.asyncio
    async def test_queue_info(self, queue_manager):
        """Test getting queue info for a model."""
        await queue_manager.enqueue(
            model_id="test-model",
            modality="text",
            input_data={"prompt": "Hello"},
        )
        
        info = queue_manager.get_queue_info("test-model")
        
        assert info["model_id"] == "test-model"
        assert "queue_depth" in info
        assert "active_count" in info


class TestQueueWithErrors:
    """Test queue behavior with errors."""
    
    @pytest.fixture
    def error_queue_manager(self):
        """Queue manager with an error-throwing executor."""
        manager = RequestQueueManager()
        
        def error_executor(request):
            if "error" in request.input_data.get("prompt", ""):
                raise ValueError("Simulated error")
            return {"result": "ok"}
        
        manager.configure(executor=error_executor)
        return manager
    
    @pytest.mark.asyncio
    async def test_request_failure(self, error_queue_manager):
        """Test that failed requests are marked as failed."""
        request = await error_queue_manager.enqueue(
            model_id="test-model",
            modality="text",
            input_data={"prompt": "trigger error"},
        )
        
        completed = await error_queue_manager.wait_for_completion(request, timeout=5.0)
        
        assert completed.status == "failed"
        assert completed.error is not None
        assert "Simulated error" in completed.error
