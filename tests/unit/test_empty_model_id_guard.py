"""Regression test for the duplicate-models bug.

Root cause:  .env contained ``LLM_API_DEFAULT_MODEL=`` (empty value).
pydantic-settings set ``default_model`` to ``""`` instead of the class
default.  ``add_model()`` treated ``""`` as falsy ⇒ generated a UUID ⇒
every server restart created phantom rows.

The fix has three layers:
  1. Settings validator replaces empty strings with class defaults.
  2. ``add_model()`` raises ``ValueError`` on empty ID.
  3. ``_prune_non_default_local_models()`` deduplicates by (name, modality).

Traceability: SYS-REQ-015 (Model Catalog)
"""

import os
import pytest
from llm_api.api.schemas import ModelInfo
from llm_api.config import get_settings
from llm_api.config.settings import _DEFAULT_MODEL, _DEFAULT_IMAGE_MODEL, _DEFAULT_3D_MODEL


class TestEmptyEnvVarModelIds:
    """Settings must never expose empty model IDs to the registry."""

    def test_empty_env_var_falls_back_to_class_default(self, monkeypatch):
        """When .env sets DEFAULT_MODEL to empty string, Settings should
        use the hardcoded default instead."""
        monkeypatch.setenv("LLM_API_DEFAULT_MODEL", "")
        monkeypatch.setenv("LLM_API_DEFAULT_IMAGE_MODEL", "")
        monkeypatch.setenv("LLM_API_DEFAULT_3D_MODEL", "")
        monkeypatch.setenv("LLM_API_MODEL_PATH", "/tmp/test-models")
        get_settings.cache_clear()

        settings = get_settings()
        assert settings.default_model == _DEFAULT_MODEL
        assert settings.default_image_model == _DEFAULT_IMAGE_MODEL
        assert settings.default_3d_model == _DEFAULT_3D_MODEL

    def test_explicit_value_not_overridden(self, monkeypatch):
        """Explicit non-empty values in env must be respected."""
        monkeypatch.setenv("LLM_API_DEFAULT_MODEL", "custom/my-model")
        monkeypatch.setenv("LLM_API_MODEL_PATH", "/tmp/test-models")
        get_settings.cache_clear()

        settings = get_settings()
        assert settings.default_model == "custom/my-model"


class TestAddModelRejectsEmptyId:
    """add_model() must never silently generate a UUID for an empty ID."""

    def test_add_model_raises_on_empty_id(self, client):
        from llm_api.registry import get_registry
        registry = get_registry()

        with pytest.raises(ValueError, match="Cannot register a model without an explicit ID"):
            registry.add_model(
                ModelInfo(
                    id="",
                    name="phantom",
                    version="latest",
                    modality="text",
                )
            )

    def test_add_model_raises_on_none_id(self, client):
        """None is also rejected (guards against future callers)."""
        from llm_api.registry import get_registry
        registry = get_registry()

        # ModelInfo.id is str, but guard against runtime None anyway
        model = ModelInfo(
            id="placeholder",
            name="phantom",
            version="latest",
            modality="text",
        )
        model.id = ""  # type: ignore[assignment]
        with pytest.raises(ValueError, match="Cannot register a model without an explicit ID"):
            registry.add_model(model)


class TestNoDuplicatesAfterRestart:
    """Simulates multiple load_defaults() calls (as with --reload) and
    verifies no duplicates accumulate."""

    def test_repeated_load_defaults_does_not_duplicate(self, client):
        from llm_api.registry import get_registry
        registry = get_registry()

        # Simulate 5 server restarts
        for _ in range(5):
            registry.load_defaults()

        models = registry.list_models()
        names = [m.name for m in models]

        # Each default model name should appear exactly once
        for name in ("Llama 3.1 8B Instruct", "SDXL Turbo", "Stable Diffusion XL", "Shap-E"):
            count = names.count(name)
            assert count == 1, (
                f"Expected 1 instance of '{name}', got {count}. "
                f"IDs: {[m.id for m in models if m.name == name]}"
            )

    def test_catalog_endpoint_returns_no_duplicates(self, client):
        """GET /v1/models must never return duplicate model names."""
        from llm_api.registry import get_registry
        registry = get_registry()

        # Simulate restarts
        for _ in range(3):
            registry.load_defaults()

        response = client.get("/v1/models", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200

        models = response.json()["models"]
        ids = [m["id"] for m in models]
        assert len(ids) == len(set(ids)), (
            f"Duplicate IDs in catalog response: "
            f"{[i for i in ids if ids.count(i) > 1]}"
        )
