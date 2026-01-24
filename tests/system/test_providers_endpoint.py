"""TEST-SYS-008: Provider list endpoint
Traceability: SYS-REQ-002
"""


class TestProvidersEndpoint:
    """System tests for the /v1/providers endpoint."""

    def test_providers_returns_list(self, client):
        response = client.get("/v1/providers", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert isinstance(data["providers"], list)

    def test_providers_include_local(self, client):
        response = client.get("/v1/providers", headers={"X-API-Key": "test-key"})
        data = response.json()
        names = [p["name"] for p in data["providers"]]
        assert "local" in names

    def test_local_provider_is_always_configured(self, client):
        response = client.get("/v1/providers", headers={"X-API-Key": "test-key"})
        data = response.json()
        local = next(p for p in data["providers"] if p["name"] == "local")
        assert local["configured"] is True
        assert "text" in local["supported_modalities"]
        assert "image" in local["supported_modalities"]
        assert "3d" in local["supported_modalities"]

    def test_commercial_providers_listed(self, client):
        response = client.get("/v1/providers", headers={"X-API-Key": "test-key"})
        data = response.json()
        names = [p["name"] for p in data["providers"]]
        assert "openai" in names
        assert "anthropic" in names
        assert "google" in names
        assert "azure" in names
        assert "xai" in names

    def test_unconfigured_provider_shows_false(self, client):
        response = client.get("/v1/providers", headers={"X-API-Key": "test-key"})
        data = response.json()
        openai = next(p for p in data["providers"] if p["name"] == "openai")
        # In test env, no OpenAI key is set
        assert openai["configured"] is False

    def test_requires_auth(self, client):
        response = client.get("/v1/providers")
        assert response.status_code == 401
