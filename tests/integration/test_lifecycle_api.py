"""Integration tests for model lifecycle API endpoints.

Tests the actual lifecycle router endpoints with mocked dependencies.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_registry():
    """Create a mock model registry."""
    with patch("llm_api.api.lifecycle_router.get_registry") as mock:
        registry = MagicMock()
        mock.return_value = registry
        yield registry


@pytest.fixture
def mock_lifecycle_manager():
    """Create a mock lifecycle manager."""
    with patch("llm_api.api.lifecycle_router.get_lifecycle_manager") as mock:
        manager = MagicMock()
        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_queue_manager():
    """Create a mock queue manager."""
    with patch("llm_api.api.lifecycle_router.get_queue_manager") as mock:
        queue = MagicMock()
        mock.return_value = queue
        yield queue


@pytest.fixture
def app(mock_lifecycle_manager, mock_registry, mock_queue_manager):
    """Create a test app with mocked dependencies."""
    from llm_api.main import create_app
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


class TestModelStatus:
    """Test GET /v1/models/{model_id}/status endpoint."""
    
    def test_get_model_status_loaded(self, client, mock_lifecycle_manager, mock_registry):
        """Test getting status of a loaded model."""
        mock_registry.get_model.return_value = {"model_id": "llama-2-7b", "name": "Llama 2"}
        mock_lifecycle_manager.get_status.return_value = "loaded"
        
        response = client.get("/v1/models/llama-2-7b/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "llama-2-7b"
        assert data["runtime_status"] == "loaded"
    
    def test_get_model_status_unloaded(self, client, mock_lifecycle_manager, mock_registry):
        """Test getting status of an unloaded model."""
        mock_registry.get_model.return_value = {"model_id": "llama-2-7b", "name": "Llama 2"}
        mock_lifecycle_manager.get_status.return_value = "unloaded"
        
        response = client.get("/v1/models/llama-2-7b/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["runtime_status"] == "unloaded"
    
    def test_get_model_status_not_found(self, client, mock_lifecycle_manager, mock_registry):
        """Test getting status of non-existent model."""
        mock_registry.get_model.return_value = None
        
        response = client.get("/v1/models/nonexistent/status")
        
        assert response.status_code == 404


class TestLoadModel:
    """Test POST /v1/models/{model_id}/load endpoint."""
    
    def test_load_model_success_wait(self, client, mock_lifecycle_manager, mock_registry):
        """Test synchronously loading a model with wait=True."""
        mock_registry.get_model.return_value = {"model_id": "llama-2-7b", "name": "Llama 2"}
        mock_lifecycle_manager.get_status.return_value = "unloaded"
        mock_lifecycle_manager.load_model = AsyncMock(return_value=True)
        
        response = client.post("/v1/models/llama-2-7b/load", json={"wait": True})
        
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "llama-2-7b"
        assert data["status"] == "loaded"
    
    def test_load_model_async(self, client, mock_lifecycle_manager, mock_registry):
        """Test asynchronously loading a model (default behavior)."""
        mock_registry.get_model.return_value = {"model_id": "llama-2-7b", "name": "Llama 2"}
        mock_lifecycle_manager.get_status.return_value = "unloaded"
        mock_lifecycle_manager.load_model = AsyncMock(return_value=True)
        
        response = client.post("/v1/models/llama-2-7b/load")
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "loading"
    
    def test_load_model_already_loaded(self, client, mock_lifecycle_manager, mock_registry):
        """Test loading an already loaded model returns success."""
        mock_registry.get_model.return_value = {"model_id": "llama-2-7b", "name": "Llama 2"}
        mock_lifecycle_manager.get_status.return_value = "loaded"
        
        response = client.post("/v1/models/llama-2-7b/load")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Model already loaded"
    
    def test_load_model_not_found(self, client, mock_lifecycle_manager, mock_registry):
        """Test loading a non-existent model returns 404."""
        mock_registry.get_model.return_value = None
        
        response = client.post("/v1/models/nonexistent/load")
        
        assert response.status_code == 404


class TestUnloadModel:
    """Test POST /v1/models/{model_id}/unload endpoint."""
    
    def test_unload_model_success(self, client, mock_lifecycle_manager, mock_registry):
        """Test successfully unloading a model."""
        mock_lifecycle_manager.get_status.return_value = "loaded"
        mock_lifecycle_manager.unload_model = AsyncMock(return_value=True)
        
        response = client.post("/v1/models/llama-2-7b/unload")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unloaded"
    
    def test_unload_model_error(self, client, mock_lifecycle_manager, mock_registry):
        """Test unloading fails gracefully when model is pinned/busy."""
        mock_lifecycle_manager.get_status.return_value = "loaded"
        mock_lifecycle_manager.unload_model = AsyncMock(return_value=False)
        
        response = client.post("/v1/models/pinned-model/unload")
        
        assert response.status_code == 400


class TestListLoadedModels:
    """Test GET /v1/models/loaded endpoint."""
    
    def test_list_loaded_models(self, client, mock_lifecycle_manager, mock_registry):
        """Test listing all loaded models."""
        mock_lifecycle_manager.get_loaded_models.return_value = [
            {
                "model_id": "llama-2-7b",
                "status": "loaded",
                "memory_mb": 14000,
                "memory_bytes": 14000 * 1024 * 1024,
                "request_count": 0,
                "is_pinned": False,
                "is_busy": False,
                "busy_count": 0,
                "loaded_at": "2024-01-01T00:00:00Z",
                "last_used_at": "2024-01-01T00:00:00Z",
            },
            {
                "model_id": "llama-2-13b",
                "status": "loaded",
                "memory_mb": 26000,
                "memory_bytes": 26000 * 1024 * 1024,
                "request_count": 0,
                "is_pinned": True,
                "is_busy": False,
                "busy_count": 0,
                "loaded_at": "2024-01-01T00:00:00Z",
                "last_used_at": "2024-01-01T00:00:00Z",
            },
        ]
        
        response = client.get("/v1/models/loaded")
        
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) == 2
    
    def test_list_loaded_models_empty(self, client, mock_lifecycle_manager, mock_registry):
        """Test listing when no models are loaded."""
        mock_lifecycle_manager.get_loaded_models.return_value = []
        
        response = client.get("/v1/models/loaded")
        
        assert response.status_code == 200
        data = response.json()
        assert data["models"] == []


class TestRequestStatus:
    """Test GET /v1/requests/{request_id}/status endpoint."""
    
    def test_get_request_status(self, client, mock_queue_manager, mock_registry, mock_lifecycle_manager):
        """Test getting status of a queued request."""
        from unittest.mock import MagicMock
        mock_request = MagicMock()
        mock_request.status = "pending"
        mock_request.queue_position = 2
        mock_queue_manager.get_request.return_value = mock_request
        
        response = client.get("/v1/requests/req-123/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == "req-123"
    
    def test_get_request_status_not_found(self, client, mock_queue_manager, mock_registry, mock_lifecycle_manager):
        """Test getting status of non-existent request."""
        mock_queue_manager.get_request.return_value = None
        
        response = client.get("/v1/requests/nonexistent/status")
        
        assert response.status_code == 404


class TestCancelRequest:
    """Test POST /v1/requests/{request_id}/cancel endpoint."""
    
    def test_cancel_request_success(self, client, mock_queue_manager, mock_registry, mock_lifecycle_manager):
        """Test successfully cancelling a queued request."""
        from unittest.mock import MagicMock
        mock_request = MagicMock()
        mock_request.status = "queued"
        mock_queue_manager.get_request.return_value = mock_request
        mock_queue_manager.cancel_request.return_value = True
        
        response = client.post("/v1/requests/req-123/cancel")
        
        assert response.status_code == 200
        data = response.json()
        assert data["cancelled"] is True
    
    def test_cancel_request_not_found(self, client, mock_queue_manager, mock_registry, mock_lifecycle_manager):
        """Test cancelling a non-existent request."""
        mock_queue_manager.get_request.return_value = None
        
        response = client.post("/v1/requests/nonexistent/cancel")
        
        assert response.status_code == 404
