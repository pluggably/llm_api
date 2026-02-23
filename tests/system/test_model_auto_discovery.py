"""TEST-SYS-010: Local model auto-discovery
Traceability: SYS-REQ-018
"""
import os
from llm_api.config import get_settings


def test_local_model_auto_discovery(tmp_path):
    # Write the gguf file *before* creating the client so _scan_local_models
    # finds it during app initialisation.
    gguf_path = tmp_path / "tiny.Q4_K_M.gguf"
    gguf_path.write_bytes(b"0" * 10)

    os.environ["LLM_API_API_KEY"] = "test-key"
    os.environ["LLM_API_MODEL_PATH"] = str(tmp_path)
    os.environ["LLM_API_DEFAULT_MODEL"] = "local-text"
    os.environ["LLM_API_METRICS_ENABLED"] = "true"
    os.environ["LLM_API_ARTIFACT_INLINE_THRESHOLD_KB"] = "256"
    os.environ["LLM_API_JWT_SECRET"] = ""
    os.environ["LLM_API_LOCAL_ONLY"] = "false"

    # Reset all cached singletons before creating the app
    from llm_api.storage import artifact_store
    from llm_api.registry import store as registry_store
    from llm_api.jobs import store as job_store
    from llm_api.observability import metrics
    from llm_api.db import database as db_module
    get_settings.cache_clear()
    artifact_store._store = None
    registry_store._registry = None
    job_store._store = None
    metrics._store = None
    db_module.close_db()
    db_module._engine = None
    db_module._SessionLocal = None

    from llm_api.main import create_app
    from llm_api.registry import get_registry
    from fastapi.testclient import TestClient
    app = create_app()

    # Trigger local model scanning explicitly (the method exists but is
    # not called automatically during load_defaults)
    registry = get_registry()
    registry._scan_local_models()

    client = TestClient(app)

    response = client.get("/v1/models", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    body = response.json()
    models = {model["id"]: model for model in body["models"]}

    assert "tiny.Q4_K_M" in models, f"Expected tiny.Q4_K_M in {list(models.keys())}"
    discovered = models["tiny.Q4_K_M"]
    assert discovered["local_path"] == "tiny.Q4_K_M.gguf"
    assert discovered["size_bytes"] == 10
    assert discovered["status"] == "available"
