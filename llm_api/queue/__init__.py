"""Request queue management for handling concurrent inference requests."""
from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Literal, Optional, Set

from llm_api.config import get_settings


logger = logging.getLogger(__name__)


RequestStatus = Literal["pending", "queued", "running", "completed", "cancelled", "failed"]


@dataclass
class QueuedRequest:
    """A request waiting in the queue."""
    request_id: str
    model_id: str
    modality: str
    input_data: Dict[str, Any]
    parameters: Dict[str, Any]
    
    # State
    status: RequestStatus = "pending"
    queue_position: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Result/error
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # Async completion event
    _event: asyncio.Event = field(default_factory=asyncio.Event)
    
    # Cancellation flag
    _cancelled: bool = False


@dataclass
class RequestQueueManager:
    """Manages request queuing and execution."""
    
    # Queue per model
    queues: Dict[str, Deque[QueuedRequest]] = field(default_factory=dict)
    
    # Active requests per model
    active_requests: Dict[str, Set[str]] = field(default_factory=dict)
    
    # All tracked requests by ID
    requests: Dict[str, QueuedRequest] = field(default_factory=dict)
    
    # Executor callback
    executor: Optional[Callable[[QueuedRequest], Any]] = None
    
    # Lock
    _lock: threading.RLock = field(default_factory=threading.RLock)
    
    # Worker tasks
    _workers: Dict[str, asyncio.Task] = field(default_factory=dict)
    
    def configure(self, executor: Callable[[QueuedRequest], Any]) -> None:
        """Configure the queue manager with an executor."""
        self.executor = executor
    
    async def enqueue(
        self,
        model_id: str,
        modality: str,
        input_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> QueuedRequest:
        """
        Enqueue a request for processing.
        
        Returns the QueuedRequest which can be awaited for completion.
        """
        settings = get_settings()
        
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        request = QueuedRequest(
            request_id=request_id,
            model_id=model_id,
            modality=modality,
            input_data=input_data,
            parameters=parameters or {},
        )
        
        with self._lock:
            # Check queue depth limit
            if model_id not in self.queues:
                self.queues[model_id] = deque()
            
            queue = self.queues[model_id]
            max_depth = settings.max_queue_depth
            
            if len(queue) >= max_depth:
                request.status = "failed"
                request.error = "Queue full"
                request._event.set()
                return request
            
            # Add to queue
            queue.append(request)
            request.status = "queued"
            request.queue_position = len(queue)
            self.requests[request_id] = request
            
            # Start worker if not running
            if model_id not in self._workers or self._workers[model_id].done():
                self._workers[model_id] = asyncio.create_task(self._process_queue(model_id))
        
        # Update queue positions
        self._update_positions(model_id)
        
        return request
    
    async def wait_for_completion(
        self,
        request: QueuedRequest,
        timeout: Optional[float] = None,
    ) -> QueuedRequest:
        """Wait for a request to complete."""
        try:
            await asyncio.wait_for(request._event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        return request
    
    def get_request(self, request_id: str) -> Optional[QueuedRequest]:
        """Get a request by ID."""
        with self._lock:
            return self.requests.get(request_id)
    
    def get_queue_position(self, request_id: str) -> Optional[int]:
        """Get the current queue position of a request."""
        with self._lock:
            request = self.requests.get(request_id)
            if request and request.status == "queued":
                return request.queue_position
            return None
    
    def cancel_request(self, request_id: str) -> bool:
        """
        Cancel a queued or running request.
        
        Returns True if cancellation was initiated.
        """
        with self._lock:
            request = self.requests.get(request_id)
            if not request:
                return False
            
            if request.status in ("completed", "cancelled", "failed"):
                return False
            
            request._cancelled = True
            
            if request.status == "queued":
                # Remove from queue
                model_id = request.model_id
                if model_id in self.queues:
                    try:
                        self.queues[model_id].remove(request)
                    except ValueError:
                        pass
                
                request.status = "cancelled"
                request.completed_at = datetime.now(timezone.utc)
                request._event.set()
                self._update_positions(model_id)
            
            # If running, the executor should check _cancelled flag
            return True
    
    def get_queue_info(self, model_id: str) -> Dict[str, Any]:
        """Get queue information for a model."""
        with self._lock:
            queue = self.queues.get(model_id, deque())
            active = self.active_requests.get(model_id, set())
            
            return {
                "model_id": model_id,
                "queue_depth": len(queue),
                "active_count": len(active),
                "queued_request_ids": [r.request_id for r in queue],
                "active_request_ids": list(active),
            }
    
    def _update_positions(self, model_id: str) -> None:
        """Update queue positions for all requests in a queue."""
        with self._lock:
            queue = self.queues.get(model_id, deque())
            for i, request in enumerate(queue):
                request.queue_position = i + 1
    
    async def _process_queue(self, model_id: str) -> None:
        """Process requests from a model's queue."""
        settings = get_settings()
        max_concurrent = settings.max_concurrent_requests_per_model
        
        while True:
            request = None
            
            with self._lock:
                queue = self.queues.get(model_id)
                if not queue:
                    break
                
                # Check concurrent limit
                active = self.active_requests.get(model_id, set())
                if len(active) >= max_concurrent:
                    # Wait and retry
                    pass
                else:
                    # Get next request
                    request = queue.popleft()
                    if model_id not in self.active_requests:
                        self.active_requests[model_id] = set()
                    self.active_requests[model_id].add(request.request_id)
                    request.status = "running"
                    request.started_at = datetime.now(timezone.utc)
            
            if request is None:
                await asyncio.sleep(0.1)
                continue
            
            self._update_positions(model_id)
            
            try:
                if request._cancelled:
                    request.status = "cancelled"
                elif self.executor:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self.executor, request
                    )
                    if request._cancelled:
                        request.status = "cancelled"
                    else:
                        request.result = result
                        request.status = "completed"
                else:
                    request.status = "failed"
                    request.error = "No executor configured"
            except Exception as e:
                request.status = "failed"
                request.error = str(e)
            finally:
                request.completed_at = datetime.now(timezone.utc)
                request._event.set()
                
                with self._lock:
                    active = self.active_requests.get(model_id, set())
                    active.discard(request.request_id)
        
        # Clean up worker
        with self._lock:
            if model_id in self._workers:
                del self._workers[model_id]

    async def shutdown(self, timeout: float = 10.0) -> None:
        """Cancel running worker tasks and wait up to timeout seconds."""
        with self._lock:
            tasks = list(self._workers.values())
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=max(0.0, timeout),
                )
            except asyncio.TimeoutError:
                pending = [task for task in tasks if not task.done()]
                if pending:
                    logger.warning(
                        "Queue shutdown timed out with %d worker task(s) still pending",
                        len(pending),
                    )
        with self._lock:
            self._workers.clear()


# Global instance
_queue_manager: Optional[RequestQueueManager] = None


def get_queue_manager() -> RequestQueueManager:
    """Get the global queue manager instance."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = RequestQueueManager()
    return _queue_manager
