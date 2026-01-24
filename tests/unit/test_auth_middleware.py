"""TEST-UNIT-003: Auth middleware
Traceability: SYS-REQ-014
"""
class TestAuthMiddleware:
    """Unit tests for authentication middleware."""

    def test_valid_api_key_passes(self, client_factory):
        client = client_factory({"api_key": "test-key"})
        response = client.get("/v1/models", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200

    def test_invalid_api_key_returns_401(self, client_factory):
        client = client_factory({"api_key": "test-key"})
        response = client.get("/v1/models", headers={"X-API-Key": "wrong"})
        assert response.status_code == 401

    def test_missing_api_key_returns_401(self, client_factory):
        client = client_factory({"api_key": "test-key"})
        response = client.get("/v1/models")
        assert response.status_code == 401

    def test_valid_jwt_passes(self, client_factory):
        client = client_factory({"jwt_secret": "secret", "api_key": "test-key"})
        response = client.get("/v1/models", headers={"Authorization": "Bearer valid-token"})
        assert response.status_code == 200

    def test_expired_jwt_returns_401(self, client_factory):
        client = client_factory({"jwt_secret": "secret", "api_key": "test-key"})
        response = client.get("/v1/models", headers={"Authorization": "Bearer expired"})
        assert response.status_code == 401

    def test_local_only_mode_skips_auth(self, client_factory):
        client = client_factory({"local_only": "true", "api_key": "test-key"})
        response = client.get("/v1/models")
        assert response.status_code == 200
