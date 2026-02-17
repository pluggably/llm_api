"""Shared pytest fixtures for LLM API Gateway tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient

from llm_api.config import get_settings
from llm_api.registry.store import ModelRegistry
from llm_api.api.schemas import ModelInfo
from llm_api.storage import artifact_store
from llm_api.adapters.base import ProviderError
from llm_api.registry import store as registry_store
from llm_api.jobs import store as job_store
from llm_api.observability import metrics
from llm_api.db import database as db_module


def _reset_state():
    get_settings.cache_clear()
    artifact_store._store = None
    registry_store._registry = None
    job_store._store = None
    metrics._store = None
    # Close and reset database connection for isolation
    db_module.close_db()
    db_module._engine = None
    db_module._SessionLocal = None


def _build_client(tmp_path: Path, overrides: dict | None = None) -> TestClient:
    overrides = overrides or {}
    os.environ["LLM_API_API_KEY"] = overrides.get("api_key", "test-key")
    os.environ["LLM_API_MODEL_PATH"] = str(tmp_path)
    os.environ["LLM_API_METRICS_ENABLED"] = overrides.get("metrics_enabled", "true")
    os.environ["LLM_API_ARTIFACT_INLINE_THRESHOLD_KB"] = overrides.get("artifact_inline_threshold_kb", "256")
    os.environ["LLM_API_DEFAULT_MODEL"] = overrides.get("default_model", "local-text")
    os.environ["LLM_API_JWT_SECRET"] = overrides.get("jwt_secret", "")
    os.environ["LLM_API_LOCAL_ONLY"] = overrides.get("local_only", "false")

    _reset_state()
    from llm_api.main import create_app
    app = create_app()
    return TestClient(app)


@pytest.fixture
def client(tmp_path):
    """FastAPI TestClient fixture."""
    return _build_client(tmp_path)


@pytest.fixture
def client_factory(tmp_path):
    """Factory to create a client with env overrides."""
    def _factory(overrides: dict | None = None) -> TestClient:
        return _build_client(tmp_path, overrides)

    return _factory


@pytest.fixture(autouse=True)
def patch_local_runner(monkeypatch):
    from llm_api.runner.local_runner import LocalRunner

    def _generate_text(self, prompt, model_path=None, model_id=None, hf_token=None):
        if prompt == "RAISE_ERROR":
            raise ProviderError(500, "Simulated error")
        return f"local:{prompt}"

    def _generate_image(self, prompt, model_path=None, model_id=None, **kwargs):
        return b"LOCAL_IMAGE"
    
    def _generate_3d(self, prompt, model_path=None, model_id=None, **kwargs):
        return b"LOCAL_3D"

    monkeypatch.setattr(LocalRunner, "generate_text", _generate_text)
    monkeypatch.setattr(LocalRunner, "generate_image", _generate_image)
    monkeypatch.setattr(LocalRunner, "generate_3d", _generate_3d)


# ============================================================================
# Mock Model Fixtures
# ============================================================================

@pytest.fixture
def mock_text_model():
    return "text"


@pytest.fixture
def mock_image_model():
    return "image"


@pytest.fixture
def mock_3d_model():
    return "3d"


@pytest.fixture
def mock_vision_model():
    return "vision"


# ============================================================================
# Mock Registry Fixtures
# ============================================================================

@pytest.fixture
def mock_registry(tmp_path):
    registry = ModelRegistry()
    registry.add_model(
        ModelInfo(
            id="gpt-4",
            name="gpt-4",
            version="latest",
            modality="text",
            provider="openai",
        )
    )
    registry.add_model(
        ModelInfo(
            id="deepseek-r1",
            name="deepseek-r1",
            version="latest",
            modality="text",
            provider="local",
            local_path="deepseek.bin",
        )
    )
    return registry


@pytest.fixture
def empty_registry():
    return ModelRegistry()


@pytest.fixture
def mock_registry_many_models():
    registry = ModelRegistry()
    for idx in range(50):
        registry.add_model(
            ModelInfo(
                id=f"model-{idx}",
                name=f"model-{idx}",
                version="latest",
                modality="text",
                provider="openai",
            )
        )
    return registry


@pytest.fixture
def mock_model_registry_loaded():
    registry = ModelRegistry()
    registry.ready = True
    return registry


@pytest.fixture
def mock_model_registry_uninitialized():
    registry = ModelRegistry()
    registry.ready = False
    return registry


# ============================================================================
# Mock Settings Fixtures
# ============================================================================

@pytest.fixture
def mock_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_MODEL_PATH", str(tmp_path))
    get_settings.cache_clear()
    return get_settings()


# ============================================================================
# Mock Provider Fixtures
# ============================================================================

@pytest.fixture
def mock_openai_rate_limit():
    return 429


@pytest.fixture
def mock_openai_auth_error():
    return 401


@pytest.fixture
def mock_anthropic_overloaded():
    return 503


@pytest.fixture
def mock_local_runner_oom():
    return 500


@pytest.fixture
def mock_provider_timeout():
    return 504


@pytest.fixture
def mock_text_model_with_error():
    return "error"


# ============================================================================
# Storage Fixtures
# ============================================================================

@pytest.fixture
def tmp_model_dir(tmp_path):
    """Temporary directory for model storage with isolated database.
    
    This fixture ensures tests don't pollute the production database by:
    1. Setting LLM_API_MODEL_PATH to the temp directory
    2. Resetting the settings cache and database connection
    """
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    
    # Isolate from production database
    os.environ["LLM_API_MODEL_PATH"] = str(model_dir)
    _reset_state()
    
    yield model_dir
    
    # Cleanup - restore to avoid affecting other tests
    _reset_state()


# ============================================================================
# Download Job Fixtures
# ============================================================================

@pytest.fixture
def running_download_job(client):
    payload = {
        "model": {"id": "model-run", "name": "model-run", "version": "latest", "modality": "text"},
        "source": {"type": "local", "uri": "./models/model-run"},
    }
    response = client.post("/v1/models/download", json=payload, headers={"X-API-Key": "test-key"})
    data = response.json()
    return data["job_id"]


@pytest.fixture
def completed_download(client):
    payload = {
        "model": {"id": "model-complete", "name": "model-complete", "version": "latest", "modality": "text"},
        "source": {"type": "local", "uri": "./models/model-complete"},
    }
    response = client.post("/v1/models/download", json=payload, headers={"X-API-Key": "test-key"})
    return response.json()["job_id"]


@pytest.fixture
def failed_download_job(client):
    payload = {
        "model": {"id": "model-fail", "name": "model-fail", "version": "latest", "modality": "text"},
        "source": {"type": "local", "uri": "./models/model-fail"},
    }
    response = client.post("/v1/models/download", json=payload, headers={"X-API-Key": "test-key"})
    job_id = response.json()["job_id"]
    job_store.get_job_store().update_job(job_id, status="failed", progress_pct=0, error="download failed")
    return job_id


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def time_travel():
    """Mock time for testing expiry."""
    return None
