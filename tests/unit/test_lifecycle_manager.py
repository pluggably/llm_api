"""Tests for model lifecycle management."""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone

from llm_api.lifecycle import ModelLifecycleManager, get_lifecycle_manager


@pytest.fixture
def lifecycle_manager():
    """Create a fresh lifecycle manager for testing."""
    manager = ModelLifecycleManager()
    
    # Mock load/unload callbacks
    loaded_models = {}
    
    def mock_load(model_id: str):
        loaded_models[model_id] = {"id": model_id, "loaded": True}
        return loaded_models[model_id]
    
    def mock_unload(model_id: str, instance):
        if model_id in loaded_models:
            del loaded_models[model_id]
    
    manager.configure(
        load_callback=mock_load,
        unload_callback=mock_unload,
    )
    
    return manager


class TestModelLifecycleManager:
    """Test suite for ModelLifecycleManager."""
    
    def test_initial_status_unloaded(self, lifecycle_manager):
        """Test that models start as unloaded."""
        status = lifecycle_manager.get_status("test-model")
        assert status == "unloaded"
    
    @pytest.mark.asyncio
    async def test_load_model(self, lifecycle_manager):
        """Test loading a model."""
        result = await lifecycle_manager.load_model("test-model")
        
        assert result is not None
        assert result["id"] == "test-model"
        assert lifecycle_manager.get_status("test-model") == "loaded"
    
    @pytest.mark.asyncio
    async def test_load_model_idempotent(self, lifecycle_manager):
        """Test that loading an already loaded model returns the same instance."""
        result1 = await lifecycle_manager.load_model("test-model")
        result2 = await lifecycle_manager.load_model("test-model")
        
        assert result1 is result2
    
    @pytest.mark.asyncio
    async def test_unload_model(self, lifecycle_manager):
        """Test unloading a model."""
        await lifecycle_manager.load_model("test-model")
        assert lifecycle_manager.get_status("test-model") == "loaded"
        
        success = await lifecycle_manager.unload_model("test-model")
        assert success
        assert lifecycle_manager.get_status("test-model") == "unloaded"
    
    @pytest.mark.asyncio
    async def test_pinned_model_not_unloaded(self, lifecycle_manager):
        """Test that pinned models cannot be unloaded."""
        await lifecycle_manager.load_model("test-model", is_pinned=True)
        
        success = await lifecycle_manager.unload_model("test-model")
        assert not success
        assert lifecycle_manager.get_status("test-model") == "loaded"
    
    @pytest.mark.asyncio
    async def test_pinned_model_force_unload(self, lifecycle_manager):
        """Test that pinned models can be force unloaded."""
        await lifecycle_manager.load_model("test-model", is_pinned=True)
        
        success = await lifecycle_manager.unload_model("test-model", force=True)
        assert success
        assert lifecycle_manager.get_status("test-model") == "unloaded"
    
    @pytest.mark.asyncio
    async def test_busy_model_not_unloaded(self, lifecycle_manager):
        """Test that busy models cannot be unloaded."""
        await lifecycle_manager.load_model("test-model")
        lifecycle_manager.mark_busy("test-model")
        
        assert lifecycle_manager.get_status("test-model") == "busy"
        
        success = await lifecycle_manager.unload_model("test-model")
        assert not success
    
    def test_mark_busy_and_idle(self, lifecycle_manager):
        """Test marking models busy and idle."""
        # Can't mark busy if not loaded
        assert not lifecycle_manager.mark_busy("test-model")
    
    @pytest.mark.asyncio
    async def test_mark_busy_loaded_model(self, lifecycle_manager):
        """Test marking a loaded model as busy."""
        await lifecycle_manager.load_model("test-model")
        
        assert lifecycle_manager.mark_busy("test-model")
        assert lifecycle_manager.get_status("test-model") == "busy"
        
        lifecycle_manager.mark_idle("test-model")
        assert lifecycle_manager.get_status("test-model") == "loaded"
    
    @pytest.mark.asyncio
    async def test_get_loaded_models(self, lifecycle_manager):
        """Test listing loaded models."""
        await lifecycle_manager.load_model("model-1")
        await lifecycle_manager.load_model("model-2", is_pinned=True)
        
        loaded = lifecycle_manager.get_loaded_models()
        assert len(loaded) == 2
        
        model_ids = [m["model_id"] for m in loaded]
        assert "model-1" in model_ids
        assert "model-2" in model_ids
        
        pinned = [m for m in loaded if m["is_pinned"]]
        assert len(pinned) == 1
        assert pinned[0]["model_id"] == "model-2"


class TestLRUEviction:
    """Test LRU eviction behavior."""
    
    @pytest.fixture
    def small_capacity_manager(self):
        """Manager with max 2 loaded models."""
        manager = ModelLifecycleManager()
        
        loaded = {}
        def mock_load(model_id):
            loaded[model_id] = {"id": model_id}
            return loaded[model_id]
        
        def mock_unload(model_id, instance):
            if model_id in loaded:
                del loaded[model_id]
        
        manager.configure(load_callback=mock_load, unload_callback=mock_unload)
        return manager
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self, small_capacity_manager, monkeypatch):
        """Test that LRU model is evicted when limit is reached."""
        # Patch settings for max 2 models
        from llm_api.config import Settings
        mock_settings = Settings(
            api_key="test",
            max_loaded_models=2,
            model_idle_timeout_seconds=0,
        )
        monkeypatch.setattr("llm_api.lifecycle.get_settings", lambda: mock_settings)
        
        manager = small_capacity_manager
        
        await manager.load_model("model-1")
        await manager.load_model("model-2")
        
        # Loading a third should evict model-1 (LRU)
        await manager.load_model("model-3")
        
        loaded = manager.get_loaded_models()
        model_ids = [m["model_id"] for m in loaded]
        
        assert len(loaded) == 2
        assert "model-1" not in model_ids
        assert "model-2" in model_ids
        assert "model-3" in model_ids
