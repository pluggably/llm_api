"""TEST-UNIT-003: Auth middleware
Traceability: SYS-REQ-014
"""
import time
import jwt as pyjwt
from unittest.mock import patch, MagicMock


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
        secret = "test-jwt-secret"
        token = pyjwt.encode(
            {"sub": "user-1", "exp": int(time.time()) + 300},
            secret,
            algorithm="HS256",
        )
        client = client_factory({"jwt_secret": secret, "api_key": "test-key"})
        # Mock user lookup since the JWT sub must resolve to a user
        with patch("llm_api.auth.dependencies.get_user_service") as mock_svc:
            mock_svc.return_value.get_user.return_value = {
                "id": "user-1",
                "email": "u@test.com",
            }
            response = client.get("/v1/models", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_expired_jwt_returns_401(self, client_factory):
        secret = "test-jwt-secret"
        token = pyjwt.encode(
            {"sub": "user-1", "exp": int(time.time()) - 60},
            secret,
            algorithm="HS256",
        )
        client = client_factory({"jwt_secret": secret, "api_key": "test-key"})
        response = client.get("/v1/models", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_local_only_mode_skips_auth(self, client_factory):
        client = client_factory({"local_only": "true", "api_key": "test-key"})
        response = client.get("/v1/models")
        assert response.status_code == 200
