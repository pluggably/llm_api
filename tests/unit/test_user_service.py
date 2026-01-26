"""Tests for user authentication and management."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from llm_api.users import UserService, _hash_password, _verify_password, _hash_token


class TestPasswordHashing:
    """Test password hashing functions."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test-password-123"
        hashed, salt = _hash_password(password)
        
        assert hashed is not None
        assert salt is not None
        assert len(hashed) == 64  # SHA256 hex
        assert len(salt) == 32  # 16 bytes hex
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test-password-123"
        hashed, salt = _hash_password(password)
        
        assert _verify_password(password, hashed, salt)
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test-password-123"
        hashed, salt = _hash_password(password)
        
        assert not _verify_password("wrong-password", hashed, salt)
    
    def test_hash_token(self):
        """Test token hashing."""
        token = "test-token-abc123"
        hashed = _hash_token(token)
        
        assert hashed is not None
        assert len(hashed) == 64  # SHA256 hex
        
        # Same token should produce same hash
        assert _hash_token(token) == hashed


class TestUserService:
    """Test UserService with mocked database."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        with patch("llm_api.users.get_db_session") as mock:
            session = MagicMock()
            mock.return_value.__enter__ = MagicMock(return_value=session)
            mock.return_value.__exit__ = MagicMock(return_value=False)
            yield session
    
    @pytest.fixture
    def user_service(self):
        """Create a user service instance."""
        return UserService()
    
    def test_create_invite(self, user_service, mock_db_session):
        """Test creating an invite token."""
        token = user_service.create_invite()
        
        assert token is not None
        assert len(token) > 20  # URL-safe base64
        mock_db_session.add.assert_called_once()
    
    def test_validate_invite_not_found(self, user_service, mock_db_session):
        """Test validating a non-existent invite."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        result = user_service.validate_invite("invalid-token")
        
        assert not result
    
    def test_register_without_invite_when_required(self, user_service, mock_db_session):
        """Test registration fails without invite when required."""
        with patch("llm_api.users.get_settings") as mock_settings:
            mock_settings.return_value.invite_required = True
        
            # Mock validate_invite to return False
            with patch.object(user_service, "validate_invite", return_value=False):
                result = user_service.register(
                    email="test@example.com",
                    password="password123",
                    invite_token=None,
                )
        
        assert result is None
    
    def test_authenticate_user_not_found(self, user_service, mock_db_session):
        """Test authentication with non-existent user."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        result = user_service.authenticate("test@example.com", "password")
        
        assert result is None
    
    def test_list_api_tokens(self, user_service, mock_db_session):
        """Test listing API tokens."""
        mock_token = MagicMock()
        mock_token.id = "token-1"
        mock_token.name = "Test Token"
        mock_token.scopes = ["read"]
        mock_token.created_at.isoformat.return_value = "2024-01-01T00:00:00Z"
        mock_token.last_used_at = None
        mock_token.expires_at = None
        
        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_token]
        
        tokens = user_service.list_api_tokens("user-1")
        
        assert len(tokens) == 1
        assert tokens[0]["id"] == "token-1"
        assert tokens[0]["name"] == "Test Token"
    
    def test_revoke_token_not_found(self, user_service, mock_db_session):
        """Test revoking a non-existent token."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        result = user_service.revoke_api_token("user-1", "invalid-token")
        
        assert not result
    
    def test_revoke_token_success(self, user_service, mock_db_session):
        """Test successful token revocation."""
        mock_token = MagicMock()
        mock_token.is_active = True
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_token
        
        result = user_service.revoke_api_token("user-1", "token-1")
        
        assert result
        assert not mock_token.is_active
    
    def test_list_provider_keys(self, user_service, mock_db_session):
        """Test listing provider keys."""
        mock_key = MagicMock()
        mock_key.id = "key-1"
        mock_key.provider = "openai"
        mock_key.created_at.isoformat.return_value = "2024-01-01T00:00:00Z"
        
        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_key]
        
        keys = user_service.list_provider_keys("user-1")
        
        assert len(keys) == 1
        assert keys[0]["provider"] == "openai"
    
    def test_delete_provider_key_not_found(self, user_service, mock_db_session):
        """Test deleting a non-existent provider key."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        result = user_service.delete_provider_key("user-1", "openai")
        
        assert not result
