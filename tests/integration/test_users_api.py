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
    """Create a test app with mocked user service."""
    from llm_api.main import create_app
    return create_app()


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
    
    def test_get_profile(self, client, mock_user_service):
        """Test getting user profile (not yet implemented)."""
        response = client.get("/v1/users/me")
        
        # Endpoint returns 501 as user context is not implemented
        assert response.status_code == 501
    
    def test_update_profile(self, client, mock_user_service):
        """Test updating user profile (not yet implemented)."""
        response = client.patch("/v1/users/me", json={
            "default_model": "llama-2-13b",
        })
        
        # Endpoint returns 501 as user context is not implemented
        assert response.status_code == 501


class TestAPITokens:
    """Test /v1/users/tokens endpoints."""
    
    def test_create_api_token(self, client, mock_user_service):
        """Test creating an API token."""
        mock_user_service.create_api_token.return_value = (
            "secret-token-value",
            {"id": "tok-123", "name": "My Token", "created_at": "2024-01-01T00:00:00Z"},
        )
        
        response = client.post("/v1/users/tokens", json={
            "name": "My Token",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert "token" in data
    
    def test_list_api_tokens(self, client, mock_user_service):
        """Test listing API tokens."""
        mock_user_service.list_api_tokens.return_value = [
            {"id": "tok-1", "name": "Token 1", "created_at": "2024-01-01"},
            {"id": "tok-2", "name": "Token 2", "created_at": "2024-01-02"},
        ]
        
        response = client.get("/v1/users/tokens")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_revoke_api_token(self, client, mock_user_service):
        """Test revoking an API token."""
        mock_user_service.revoke_api_token.return_value = True
        
        response = client.delete("/v1/users/tokens/tok-123")
        
        assert response.status_code == 200


class TestProviderKeys:
    """Test /v1/users/provider-keys endpoints."""
    
    def test_store_provider_key(self, client, mock_user_service):
        """Test storing a provider API key."""
        mock_user_service.set_provider_key.return_value = {"provider": "openai", "created": True}
        
        response = client.post("/v1/users/provider-keys", json={
            "provider": "openai",
            "api_key": "sk-xxx",
        })
        
        assert response.status_code == 201
    
    def test_list_provider_keys(self, client, mock_user_service):
        """Test listing stored provider keys."""
        mock_user_service.list_provider_keys.return_value = [
            {"provider": "openai", "masked_key": "sk-...xxx"},
            {"provider": "anthropic", "masked_key": "sk-...yyy"},
        ]
        
        response = client.get("/v1/users/provider-keys")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_delete_provider_key(self, client, mock_user_service):
        """Test deleting a provider key."""
        mock_user_service.delete_provider_key.return_value = True
        
        response = client.delete("/v1/users/provider-keys/openai")
        
        assert response.status_code == 200


class TestInvites:
    """Test /v1/users/invites endpoint."""
    
    def test_create_invite(self, client, mock_user_service):
        """Test creating an invite code."""
        mock_user_service.create_invite.return_value = "inv-abc123"
        
        response = client.post("/v1/users/invites", json={})
        
        assert response.status_code == 201
        data = response.json()
        assert "invite_token" in data
