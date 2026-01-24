"""TEST-SYS-002: Model catalog endpoint
Traceability: SYS-REQ-015
"""
from llm_api.registry import store as registry_store
from llm_api.api.schemas import ModelInfo, ModelCapabilities


class TestModelCatalogEndpoint:
    """System tests for model catalog endpoint."""

    def test_catalog_returns_available_models(self, client, mock_registry):
        registry_store._registry = mock_registry
        response = client.get("/v1/models", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert len(response.json()["models"]) >= 2

    def test_catalog_includes_capabilities(self, client, mock_registry):
        model = ModelInfo(
            id="cap",
            name="cap",
            version="latest",
            modality="text",
            capabilities=ModelCapabilities(max_context_tokens=4096),
        )
        mock_registry.add_model(model)
        registry_store._registry = mock_registry
        response = client.get("/v1/models", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert any(m.get("capabilities") for m in response.json()["models"])

    def test_catalog_filter_by_modality(self, client, mock_registry):
        image_model = ModelInfo(
            id="img",
            name="img",
            version="latest",
            modality="image",
        )
        mock_registry.add_model(image_model)
        registry_store._registry = mock_registry
        response = client.get("/v1/models?modality=image", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert all(m["modality"] == "image" for m in response.json()["models"])

    def test_empty_catalog_returns_empty_list(self, client, empty_registry):
        registry_store._registry = empty_registry
        response = client.get("/v1/models", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert response.json()["models"] == []

    def test_catalog_pagination(self, client, mock_registry_many_models):
        registry_store._registry = mock_registry_many_models
        response = client.get("/v1/models?limit=10", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        body = response.json()
        assert len(body["models"]) == 10
        assert body.get("next_cursor")
