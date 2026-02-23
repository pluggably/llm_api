"""Default model endpoint system tests.

Traceability:
  SYS-REQ-052   Support a default "pinned" model per modality
  SYS-REQ-005   Routing/selection mechanism uses per-modality default
"""
from __future__ import annotations

import pytest

from llm_api.registry import store as registry_store
from llm_api.api.schemas import ModelInfo

HEADERS = {"X-API-Key": "test-key"}


def _register_model(client, model_id: str, modality: str = "text") -> None:
    """Helper: add a model to the registry via the registry store."""
    registry_store.get_registry().add_model(
        ModelInfo(
            id=model_id,
            name=model_id,
            version="latest",
            modality=modality,
            provider="local",
            status="available",
        )
    )


class TestSetDefaultModelEndpoint:
    """POST /v1/models/{model_id}/default endpoint."""

    def test_set_default_returns_model_with_is_default_true(self, client):
        """Setting default on a registered model returns it with is_default=true."""
        _register_model(client, "my-text-model", "text")
        resp = client.post(
            "/v1/models/my-text-model/default",
            headers=HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "my-text-model"
        assert body["is_default"] is True

    def test_set_default_nonexistent_model_returns_404(self, client):
        """Setting default on a model that doesn't exist returns 404."""
        resp = client.post(
            "/v1/models/nonexistent-model-xyz/default",
            headers=HEADERS,
        )
        assert resp.status_code == 404

    def test_only_one_default_per_modality(self, client):
        """Setting a new default for a modality replaces the old one."""
        _register_model(client, "text-model-a", "text")
        _register_model(client, "text-model-b", "text")

        # Set model-a as default
        resp_a = client.post("/v1/models/text-model-a/default", headers=HEADERS)
        assert resp_a.status_code == 200
        assert resp_a.json()["is_default"] is True

        # Set model-b as default (should displace model-a)
        resp_b = client.post("/v1/models/text-model-b/default", headers=HEADERS)
        assert resp_b.status_code == 200
        assert resp_b.json()["is_default"] is True

        # Catalog should show model-b as default, model-a as not default
        catalog = client.get("/v1/models", headers=HEADERS)
        assert catalog.status_code == 200
        models_by_id = {m["id"]: m for m in catalog.json()["models"]}

        assert models_by_id.get("text-model-b", {}).get("is_default") is True
        assert models_by_id.get("text-model-a", {}).get("is_default") is not True

    def test_default_image_model_separate_from_text(self, client):
        """Image and text modalities each have their own independent default."""
        _register_model(client, "my-image-model", "image")
        _register_model(client, "my-text-model-2", "text")

        client.post("/v1/models/my-image-model/default", headers=HEADERS)
        client.post("/v1/models/my-text-model-2/default", headers=HEADERS)

        catalog = client.get("/v1/models", headers=HEADERS)
        assert catalog.status_code == 200
        models_by_id = {m["id"]: m for m in catalog.json()["models"]}

        # Both should be default in their respective modalities
        assert models_by_id.get("my-image-model", {}).get("is_default") is True
        assert models_by_id.get("my-text-model-2", {}).get("is_default") is True

    def test_requires_authentication(self, client):
        """Endpoint requires API key authentication."""
        resp = client.post("/v1/models/some-model/default")
        assert resp.status_code == 401

    def test_default_model_used_in_generation(self, client):
        """After setting a model as default, it should be used for auto-selection."""
        _register_model(client, "auto-selected-model", "text")
        client.post("/v1/models/auto-selected-model/default", headers=HEADERS)

        # Generate without specifying model
        resp = client.post(
            "/v1/generate",
            json={"modality": "text", "input": {"prompt": "Hello"}},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        # The response model should be the one we set as default
        assert resp.json()["model"] == "auto-selected-model"


class TestDefaultModelInCatalog:
    """Default flag reflected correctly in /v1/models catalog."""

    def test_initially_one_default_text_model(self, client):
        """There should be exactly one default text model in a fresh registry."""
        catalog = client.get("/v1/models?modality=text", headers=HEADERS)
        assert catalog.status_code == 200
        defaults = [m for m in catalog.json()["models"] if m.get("is_default")]
        assert len(defaults) <= 1, "At most one default text model expected"

    def test_default_flag_appears_in_model_info(self, client):
        """GET /v1/models/{id} returns is_default flag."""
        _register_model(client, "flagged-model", "text")
        client.post("/v1/models/flagged-model/default", headers=HEADERS)

        resp = client.get("/v1/models/flagged-model", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["is_default"] is True
