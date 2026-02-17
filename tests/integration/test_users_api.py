"""Integration tests for user management API endpoints.

Tests the actual users router endpoints with mocked user service.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_user_service():
    """Create a mock user service."""
    with patch("llm_api.api.users_router.get_user_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def app(mock_user_service):
    """Create a test app with mocked user service and auth user context."""
    from llm_api.main import create_app
    from starlette.middleware.base import BaseHTTPMiddleware

    app = create_app()

    # Inject a middleware that sets request.state.user for API-key authed
    # requests so that _get_current_user_id works in tests.
    class _SetUserMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            api_key = request.headers.get("x-api-key")
            if api_key == "test-key":
                request.state.user = {
                    "user_id": "test-user-123",
                    "email": "test@example.com",
                }
            return await call_next(request)

    app.add_middleware(_SetUserMiddleware)
    return app


@pytest.fixture
def auth_headers():
    """Auth headers using static API key (matches conftest default 'test-key')."""
    return {"X-API-Key": "test-key"}


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


class TestUserRegistration:
    """Test POST /v1/users/register endpoint."""
    
    def test_register_success(self, client, mock_user_service):
        """Test successful user registration."""
        mock_user_service.register.return_value = {
            "id": "user-123",
            "email": "test@example.com",
        }
        
        response = client.post("/v1/users/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
    
    def test_register_with_invite(self, client, mock_user_service):
        """Test registration with invite code."""
        mock_user_service.register.return_value = {
            "id": "user-123",
            "email": "test@example.com",
        }
        
        response = client.post("/v1/users/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "invite_token": "valid-invite",
        })
        
        assert response.status_code == 201
    
    def test_register_invalid_invite(self, client, mock_user_service):
        """Test registration with invalid invite code."""
        mock_user_service.register.return_value = None
        
        response = client.post("/v1/users/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "invite_token": "invalid",
        })
        
        assert response.status_code == 400


class TestUserLogin:
    """Test POST /v1/users/login endpoint."""
    
    def test_login_success(self, client, mock_user_service):
        """Test successful login returns token."""
        mock_user_service.authenticate.return_value = {
            "id": "user-123",
            "email": "test@example.com",
        }
        mock_user_service.create_api_token.return_value = ("token-value", {"id": "tok-123"})
        
        response = client.post("/v1/users/login", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
    
    def test_login_invalid_credentials(self, client, mock_user_service):
        """Test login with invalid credentials."""
        mock_user_service.authenticate.return_value = None
        
        response = client.post("/v1/users/login", json={
            "email": "test@example.com",
            "password": "WrongPassword",
        })
        
        assert response.status_code == 401


class TestUserProfile:
    """Test /v1/users/me endpoints."""
    
    def test_get_profile(self, client, mock_user_service, auth_headers):
        """Test getting user profile."""
        mock_user_service.get_user.return_value = {
            "id": "test-user-123",
            "email": "test@example.com",
        }
        response = client.get("/v1/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
    
    def test_update_profile(self, client, mock_user_service, auth_headers):
        """Test updating user profile."""
        mock_user_service.update_profile.return_value = {
            "id": "test-user-123",
            "email": "test@example.com",
            "default_model": "llama-2-13b",
        }
        response = client.patch("/v1/users/me", json={
            "default_model": "llama-2-13b",
        }, headers=auth_headers)
        
        assert response.status_code == 200


class TestAPITokens:
    """Test /v1/users/tokens endpoints."""
    
    def test_create_api_token(self, client, mock_user_service, auth_headers):
        """Test creating an API token."""
        mock_user_service.create_api_token.return_value = (
            "secret-token-value",
            {"id": "tok-123", "name": "My Token", "created_at": "2024-01-01T00:00:00Z"},
        )
        
        response = client.post("/v1/users/tokens", json={
            "name": "My Token",
        }, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert "token" in data
    
    def test_list_api_tokens(self, client, mock_user_service, auth_headers):
        """Test listing API tokens."""
        mock_user_service.list_api_tokens.return_value = [
            {"id": "tok-1", "name": "Token 1", "created_at": "2024-01-01"},
            {"id": "tok-2", "name": "Token 2", "created_at": "2024-01-02"},
        ]
        
        response = client.get("/v1/users/tokens", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_revoke_api_token(self, client, mock_user_service, auth_headers):
        """Test revoking an API token."""
        mock_user_service.revoke_api_token.return_value = True
        
        response = client.delete("/v1/users/tokens/tok-123", headers=auth_headers)
        
        assert response.status_code == 200


class TestProviderKeys:
    """Test /v1/users/provider-keys endpoints."""
    
    def test_store_provider_key(self, client, mock_user_service, auth_headers):
        """Test storing a provider API key."""
        mock_user_service.set_provider_key.return_value = {"provider": "openai", "created": True}
        
        response = client.post("/v1/users/provider-keys", json={
            "provider": "openai",
            "api_key": "sk-xxx",
        }, headers=auth_headers)
        
        assert response.status_code == 201
    
    def test_list_provider_keys(self, client, mock_user_service, auth_headers):
        """Test listing stored provider keys."""
        mock_user_service.list_provider_keys.return_value = [
            {"provider": "openai", "masked_key": "sk-...xxx"},
            {"provider": "anthropic", "masked_key": "sk-...yyy"},
        ]
        
        response = client.get("/v1/users/provider-keys", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_delete_provider_key(self, client, mock_user_service, auth_headers):
        """Test deleting a provider key."""
        mock_user_service.delete_provider_key.return_value = True
        
        response = client.delete("/v1/users/provider-keys/openai", headers=auth_headers)
        
        assert response.status_code == 200


class TestInvites:
    """Test /v1/users/invites endpoint."""
    
    def test_create_invite(self, client, mock_user_service, auth_headers):
        """Test creating an invite code."""
        mock_user_service.create_invite.return_value = "inv-abc123"
        
        response = client.post("/v1/users/invites", json={}, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert "invite_token" in data
