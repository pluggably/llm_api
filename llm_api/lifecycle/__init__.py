"""Model lifecycle management - loading, unloading, memory management."""
from __future__ import annotations

import asyncio
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Literal, Optional, Set

from llm_api.config import get_settings


RuntimeStatus = Literal["unloaded", "loading", "loaded", "busy"]


@dataclass
class LoadedModel:
    """Represents a model currently loaded in memory."""
    model_id: str
    model_instance: Any  # The actual model object
    loaded_at: datetime
    last_used_at: datetime
    is_pinned: bool = False
    memory_bytes: int = 0
    busy_count: int = 0  # Number of active requests

    @property
    def is_busy(self) -> bool:
        return self.busy_count > 0


@dataclass
class ModelLifecycleManager:
    """Manages model loading, unloading, and memory lifecycle."""
    
    # LRU cache of loaded models
    loaded_models: OrderedDict[str, LoadedModel] = field(default_factory=OrderedDict)
    
    # Set of models currently being loaded
    loading_models: Set[str] = field(default_factory=set)
    
    # Default/pinned model ID
    default_model_id: Optional[str] = None
    
    # Callbacks
    load_callback: Optional[Callable[[str], Any]] = None
    unload_callback: Optional[Callable[[str, Any], None]] = None
    
    # Lock for thread safety
    _lock: threading.RLock = field(default_factory=threading.RLock)
    
    # Background task for idle timeout
    _idle_task: Optional[asyncio.Task] = None
    
    def configure(
        self,
        default_model_id: Optional[str] = None,
        load_callback: Optional[Callable[[str], Any]] = None,
        unload_callback: Optional[Callable[[str, Any], None]] = None,
    ) -> None:
        """Configure the lifecycle manager."""
        self.default_model_id = default_model_id
        self.load_callback = load_callback
        self.unload_callback = unload_callback
    
    def get_status(self, model_id: str) -> RuntimeStatus:
        """Get the runtime status of a model."""
        with self._lock:
            if model_id in self.loading_models:
                return "loading"
            if model_id in self.loaded_models:
                model = self.loaded_models[model_id]
                return "busy" if model.is_busy else "loaded"
            return "unloaded"
    
    def get_loaded_models(self) -> List[Dict[str, Any]]:
        """Get list of currently loaded models with metadata."""
        with self._lock:
            return [
                {
                    "model_id": model.model_id,
                    "loaded_at": model.loaded_at.isoformat(),
                    "last_used_at": model.last_used_at.isoformat(),
                    "is_pinned": model.is_pinned,
                    "memory_bytes": model.memory_bytes,
                    "is_busy": model.is_busy,
                    "busy_count": model.busy_count,
                }
                for model in self.loaded_models.values()
            ]
    
    def is_loaded(self, model_id: str) -> bool:
        """Check if a model is loaded."""
        with self._lock:
            return model_id in self.loaded_models
    
    def is_loading(self, model_id: str) -> bool:
        """Check if a model is currently loading."""
        with self._lock:
            return model_id in self.loading_models
    
    async def load_model(
        self,
        model_id: str,
        is_pinned: bool = False,
        wait: bool = True,
        use_fallback: bool = False,
        fallback_model_id: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Load a model into memory.
        
        Args:
            model_id: The model to load
            is_pinned: Whether to pin the model (prevent auto-unload)
            wait: Whether to wait for loading to complete
            use_fallback: Whether to use fallback while loading
            fallback_model_id: Specific fallback model to use
        
        Returns:
            The loaded model instance, or fallback if use_fallback=True and model is loading
        """
        settings = get_settings()
        
        with self._lock:
            # Already loaded?
            if model_id in self.loaded_models:
                model = self.loaded_models[model_id]
                model.last_used_at = datetime.now(timezone.utc)
                # Move to end of LRU
                self.loaded_models.move_to_end(model_id)
                return model.model_instance
            
            # Currently loading?
            if model_id in self.loading_models:
                if use_fallback:
                    fb_id = fallback_model_id or self.default_model_id
                    if fb_id and fb_id in self.loaded_models:
                        return self.loaded_models[fb_id].model_instance
                if not wait:
                    return None
                # Wait for loading (release lock during wait)
        
        if model_id in self.loading_models:
            # Wait for loading to complete
            while model_id in self.loading_models:
                await asyncio.sleep(0.1)
            with self._lock:
                if model_id in self.loaded_models:
                    return self.loaded_models[model_id].model_instance
                return None
        
        # Need to load the model
        with self._lock:
            # Check concurrent limit
            max_loaded = settings.max_loaded_models
            non_pinned = [m for m in self.loaded_models.values() if not m.is_pinned]
            
            while len(self.loaded_models) >= max_loaded and non_pinned:
                # Evict LRU non-pinned model
                for mid in list(self.loaded_models.keys()):
                    model = self.loaded_models[mid]
                    if not model.is_pinned and not model.is_busy:
                        self._unload_model_sync(mid)
                        non_pinned = [m for m in self.loaded_models.values() if not m.is_pinned]
                        break
                else:
                    # All non-pinned models are busy, can't evict
                    break
            
            self.loading_models.add(model_id)
        
        try:
            # Actually load the model (outside lock)
            if self.load_callback:
                model_instance = self.load_callback(model_id)
            else:
                model_instance = None
            
            with self._lock:
                self.loading_models.discard(model_id)
                
                if model_instance is not None:
                    now = datetime.now(timezone.utc)
                    # Check if model should be pinned
                    should_pin = is_pinned or (model_id == self.default_model_id) or self.is_model_pinned(model_id)
                    loaded = LoadedModel(
                        model_id=model_id,
                        model_instance=model_instance,
                        loaded_at=now,
                        last_used_at=now,
                        is_pinned=should_pin,
                    )
                    self.loaded_models[model_id] = loaded
                    return model_instance
                return None
        except Exception:
            with self._lock:
                self.loading_models.discard(model_id)
            raise
    
    def _unload_model_sync(self, model_id: str) -> None:
        """Unload a model synchronously (must hold lock)."""
        if model_id not in self.loaded_models:
            return
        
        model = self.loaded_models[model_id]
        if model.is_pinned:
            return  # Can't unload pinned models
        if model.is_busy:
            return  # Can't unload busy models
        
        if self.unload_callback:
            self.unload_callback(model_id, model.model_instance)
        
        del self.loaded_models[model_id]
    
    async def unload_model(self, model_id: str, force: bool = False) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model_id: The model to unload
            force: Force unload even if pinned or busy
        
        Returns:
            True if unloaded, False otherwise
        """
        with self._lock:
            if model_id not in self.loaded_models:
                return True
            
            model = self.loaded_models[model_id]
            if not force:
                if model.is_pinned:
                    return False
                if model.is_busy:
                    return False
            
            if self.unload_callback:
                self.unload_callback(model_id, model.model_instance)
            
            del self.loaded_models[model_id]
            return True
    
    def mark_busy(self, model_id: str) -> bool:
        """Mark a model as busy (processing request)."""
        with self._lock:
            if model_id in self.loaded_models:
                self.loaded_models[model_id].busy_count += 1
                return True
            return False
    
    def mark_idle(self, model_id: str) -> None:
        """Mark a model as idle (request complete)."""
        with self._lock:
            if model_id in self.loaded_models:
                model = self.loaded_models[model_id]
                model.busy_count = max(0, model.busy_count - 1)
                model.last_used_at = datetime.now(timezone.utc)
    
    def pin_model(self, model_id: str) -> None:
        """Mark a model as pinned (prevent auto-unload).
        
        If the model is already loaded, marks it as pinned.
        Otherwise, stores the model ID to be pinned when loaded.
        """
        with self._lock:
            if model_id in self.loaded_models:
                self.loaded_models[model_id].is_pinned = True
            # Store for pinning when loaded later
            if not hasattr(self, '_pinned_model_ids'):
                self._pinned_model_ids: Set[str] = set()
            self._pinned_model_ids.add(model_id)
    
    def is_model_pinned(self, model_id: str) -> bool:
        """Check if a model should be pinned."""
        if hasattr(self, '_pinned_model_ids'):
            return model_id in self._pinned_model_ids
        return model_id == self.default_model_id

    async def check_idle_timeout(self) -> None:
        """Check for models that have exceeded idle timeout and unload them."""
        settings = get_settings()
        timeout_seconds = settings.model_idle_timeout_seconds
        
        if timeout_seconds <= 0:
            return  # Idle timeout disabled
        
        now = datetime.now(timezone.utc)
        to_unload = []
        
        with self._lock:
            for model_id, model in self.loaded_models.items():
                if model.is_pinned:
                    continue
                if model.is_busy:
                    continue
                
                idle_seconds = (now - model.last_used_at).total_seconds()
                if idle_seconds >= timeout_seconds:
                    to_unload.append(model_id)
        
        for model_id in to_unload:
            await self.unload_model(model_id)
    
    async def start_idle_monitor(self) -> None:
        """Start the background idle timeout monitor."""
        async def monitor_loop():
            try:
                while True:
                    await asyncio.sleep(30)  # Check every 30 seconds
                    await self.check_idle_timeout()
            except asyncio.CancelledError:
                pass  # Clean exit on cancellation
        
        self._idle_task = asyncio.create_task(monitor_loop())
    
    async def stop_idle_monitor(self, timeout: float = 5.0) -> None:
        """Stop the background idle timeout monitor and wait for it to exit."""
        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._idle_task), timeout=max(0.0, timeout))
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            self._idle_task = None


# Global instance
_lifecycle_manager: Optional[ModelLifecycleManager] = None


def get_lifecycle_manager() -> ModelLifecycleManager:
    """Get the global lifecycle manager instance."""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = ModelLifecycleManager()
    return _lifecycle_manager
