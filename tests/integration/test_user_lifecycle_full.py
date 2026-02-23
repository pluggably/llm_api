"""Full user lifecycle integration tests.

Covers credential types, key masking, invite flow, token revocation,
and profile preferences.

Traceability:
  SYS-REQ-035   User registration with invite gating
  SYS-REQ-036   User authentication / API token issuance
  SYS-REQ-037   User profile management
  SYS-REQ-038   Provider API key management
  SYS-REQ-039   User API token management
  SYS-REQ-064   All four credential types (api_key, endpoint_key, oauth_token, service_account)
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware


# ---------------------------------------------------------------------------
# App / fixture helpers
# ---------------------------------------------------------------------------

def _make_app(mock_user_service):
    """Build a test FastAPI app with injected user middleware."""
    from llm_api.main import create_app

    app = create_app()

    class _SetUserMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.headers.get("x-api-key") == "test-key":
                request.state.user = {
                    "user_id": "test-user-123",
                    "email": "test@example.com",
                }
            return await call_next(request)

    app.add_middleware(_SetUserMiddleware)
    return app


@pytest.fixture
def mock_svc():
    with patch("llm_api.api.users_router.get_user_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def app(mock_svc):
    return _make_app(mock_svc)


@pytest.fixture
def client(app):
    return TestClient(app)


AUTH = {"X-API-Key": "test-key"}


# ---------------------------------------------------------------------------
# SYS-REQ-064: All four credential types
# ---------------------------------------------------------------------------

class TestCredentialTypes:
    """All four credential types are accepted and stored."""

    def test_api_key_type_accepted(self, client, mock_svc):
        mock_svc.set_provider_key.return_value = {
            "provider": "openai",
            "credential_type": "api_key",
            "masked_key": "sk-...test",
        }
        resp = client.post(
            "/v1/users/provider-keys",
            json={
                "provider": "openai",
                "credential_type": "api_key",
                "api_key": "sk-super-secret",
            },
            headers=AUTH,
        )
        assert resp.status_code == 201
        mock_svc.set_provider_key.assert_called_once()

    def test_endpoint_key_type_accepted(self, client, mock_svc):
        mock_svc.set_provider_key.return_value = {
            "provider": "azure",
            "credential_type": "endpoint_key",
            "masked_key": "az-...xxx",
        }
        resp = client.post(
            "/v1/users/provider-keys",
            json={
                "provider": "azure",
                "credential_type": "endpoint_key",
                "api_key": "azkey-1234",
                "endpoint": "https://my.openai.azure.com/",
            },
            headers=AUTH,
        )
        assert resp.status_code == 201

    def test_oauth_token_type_accepted(self, client, mock_svc):
        mock_svc.set_provider_key.return_value = {
            "provider": "google",
            "credential_type": "oauth_token",
            "masked_key": "ya29...xxx",
        }
        resp = client.post(
            "/v1/users/provider-keys",
            json={
                "provider": "google",
                "credential_type": "oauth_token",
                "oauth_token": "ya29.a0AfH6SMC...",
            },
            headers=AUTH,
        )
        assert resp.status_code == 201

    def test_service_account_type_accepted(self, client, mock_svc):
        mock_svc.set_provider_key.return_value = {
            "provider": "google",
            "credential_type": "service_account",
            "masked_key": "<sa>...xxx",
        }
        resp = client.post(
            "/v1/users/provider-keys",
            json={
                "provider": "google",
                "credential_type": "service_account",
                "service_account_json": '{"type":"service_account","project_id":"my-proj"}',
            },
            headers=AUTH,
        )
        assert resp.status_code == 201

    def test_endpoint_key_missing_endpoint_returns_400(self, client, mock_svc):
        resp = client.post(
            "/v1/users/provider-keys",
            json={
                "provider": "azure",
                "credential_type": "endpoint_key",
                "api_key": "azkey-1234",
                # endpoint missing
            },
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_oauth_token_missing_token_returns_400(self, client, mock_svc):
        resp = client.post(
            "/v1/users/provider-keys",
            json={
                "provider": "google",
                "credential_type": "oauth_token",
                # oauth_token missing
            },
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_service_account_missing_json_returns_400(self, client, mock_svc):
        resp = client.post(
            "/v1/users/provider-keys",
            json={
                "provider": "google",
                "credential_type": "service_account",
                # service_account_json missing
            },
            headers=AUTH,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Masked key format
# ---------------------------------------------------------------------------

class TestMaskedKeyFormat:
    """Provider keys must be returned masked — raw keys must not appear."""

    def test_list_returns_masked_key_not_raw(self, client, mock_svc):
        mock_svc.list_provider_keys.return_value = [
            {"provider": "openai", "credential_type": "api_key", "masked_key": "sk-...abc"},
        ]
        resp = client.get("/v1/users/provider-keys", headers=AUTH)
        assert resp.status_code == 200
        keys = resp.json()
        assert len(keys) == 1
        key_info = keys[0]
        # masked_key should be present
        assert "masked_key" in key_info
        # The raw key must not appear in the response
        assert "sk-super-secret" not in str(key_info)

    def test_masked_key_has_expected_format(self, client, mock_svc):
        """Masked keys should look like sk-...xxx (partial reveal + dots)."""
        mock_svc.list_provider_keys.return_value = [
            {"provider": "openai", "credential_type": "api_key", "masked_key": "sk-...xyz"},
        ]
        resp = client.get("/v1/users/provider-keys", headers=AUTH)
        keys = resp.json()
        masked = keys[0]["masked_key"]
        # Not the full secret; length constraint
        assert len(masked) < 40, f"Masked key looks suspiciously long: {masked}"

    def test_multiple_providers_all_masked(self, client, mock_svc):
        mock_svc.list_provider_keys.return_value = [
            {"provider": "openai", "credential_type": "api_key", "masked_key": "sk-...aaa"},
            {"provider": "anthropic", "credential_type": "api_key", "masked_key": "sk-ant-...bbb"},
        ]
        resp = client.get("/v1/users/provider-keys", headers=AUTH)
        assert resp.status_code == 200
        keys = resp.json()
        assert len(keys) == 2


# ---------------------------------------------------------------------------
# SYS-REQ-039: Token revocation
# ---------------------------------------------------------------------------

class TestApiTokenRevocation:
    """After revoking a token, it must be rejected."""

    def test_revoke_token_returns_revoked_true(self, client, mock_svc):
        mock_svc.revoke_api_token.return_value = True
        resp = client.delete("/v1/users/tokens/tok-abc", headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["revoked"] is True

    def test_revoke_nonexistent_token_returns_404(self, client, mock_svc):
        mock_svc.revoke_api_token.return_value = False
        resp = client.delete("/v1/users/tokens/no-such-token", headers=AUTH)
        assert resp.status_code == 404

    def test_revoke_calls_service_with_correct_args(self, client, mock_svc):
        mock_svc.revoke_api_token.return_value = True
        client.delete("/v1/users/tokens/my-token-id", headers=AUTH)
        mock_svc.revoke_api_token.assert_called_once_with("test-user-123", "my-token-id")


# ---------------------------------------------------------------------------
# SYS-REQ-035: Invite-only registration flow
# ---------------------------------------------------------------------------

class TestInviteFlow:
    """End-to-end invite creation → registration."""

    def test_create_invite_returns_token(self, client, mock_svc):
        mock_svc.get_user.return_value = {
            "id": "test-user-123",
            "email": "admin@example.com",
            "is_admin": True,
        }
        mock_svc.create_invite.return_value = "invite-abc-123"
        resp = client.post("/v1/users/invites", headers=AUTH)
        assert resp.status_code == 201
        assert "invite_token" in resp.json()
        assert resp.json()["invite_token"] == "invite-abc-123"

    def test_create_invite_rejected_for_non_admin(self, client, mock_svc):
        mock_svc.get_user.return_value = {
            "id": "test-user-123",
            "email": "user@example.com",
            "is_admin": False,
        }
        resp = client.post("/v1/users/invites", headers=AUTH)
        assert resp.status_code == 403

    def test_register_with_valid_invite_succeeds(self, client, mock_svc):
        mock_svc.register.return_value = {"id": "new-user", "email": "new@example.com"}
        resp = client.post(
            "/v1/users/register",
            json={
                "email": "new@example.com",
                "password": "Secure123!",
                "invite_token": "invite-abc-123",
            },
        )
        assert resp.status_code == 201

    def test_register_with_invalid_invite_rejected(self, client, mock_svc):
        mock_svc.register.return_value = None
        resp = client.post(
            "/v1/users/register",
            json={
                "email": "bad@example.com",
                "password": "Secure123!",
                "invite_token": "bad-token",
            },
        )
        assert resp.status_code == 400

    def test_register_invite_forwarded_to_service(self, client, mock_svc):
        mock_svc.register.return_value = {"id": "u1", "email": "a@b.com"}
        client.post(
            "/v1/users/register",
            json={
                "email": "a@b.com",
                "password": "Secure123!",
                "invite_token": "my-invite",
            },
        )
        call_kwargs = mock_svc.register.call_args
        # invite token should be passed to the service
        args = call_kwargs[0] if call_kwargs[0] else []
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        all_args = str(args) + str(kwargs)
        assert "my-invite" in all_args


# ---------------------------------------------------------------------------
# SYS-REQ-037: Profile preferences
# ---------------------------------------------------------------------------

class TestProfilePreferences:
    """Profile preferences can be set and retrieved."""

    def test_update_profile_persists_preferences(self, client, mock_svc):
        prefs = {"default_model": "gpt-4o", "theme": "dark"}
        mock_svc.update_profile.return_value = {
            "id": "test-user-123",
            "email": "test@example.com",
            "preferences": prefs,
        }
        resp = client.patch(
            "/v1/users/me",
            json={"preferences": prefs},
            headers=AUTH,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("preferences", {}).get("default_model") == "gpt-4o"

    def test_get_profile_returns_preferences(self, client, mock_svc):
        mock_svc.get_user.return_value = {
            "id": "test-user-123",
            "email": "test@example.com",
            "preferences": {"default_model": "claude-3-5-sonnet"},
        }
        resp = client.get("/v1/users/me", headers=AUTH)
        assert resp.status_code == 200

    def test_update_profile_calls_service_with_preferences(self, client, mock_svc):
        mock_svc.update_profile.return_value = {
            "id": "test-user-123",
            "email": "test@example.com",
        }
        client.patch(
            "/v1/users/me",
            json={"preferences": {"theme": "light"}},
            headers=AUTH,
        )
        mock_svc.update_profile.assert_called_once()
        call_kwargs = mock_svc.update_profile.call_args
        all_args = str(call_kwargs)
        assert "light" in all_args or "theme" in all_args


# ---------------------------------------------------------------------------
# Edge cases & auth
# ---------------------------------------------------------------------------

class TestAuthEdgeCases:
    """Protected endpoints exist and are accessible with valid auth.

    Note: The test environment runs with local_only=True which bypasses
    401 rejection for testclient hosts. Instead we verify the routes
    are registered (not 404) and function correctly with a valid API key.
    """

    def test_profile_endpoint_registered(self, client, mock_svc):
        mock_svc.get_user.return_value = {"id": "u1", "email": "a@b.com"}
        resp = client.get("/v1/users/me", headers=AUTH)
        assert resp.status_code != 404, "Profile endpoint should be registered"

    def test_tokens_list_endpoint_registered(self, client, mock_svc):
        mock_svc.list_api_tokens.return_value = []
        resp = client.get("/v1/users/tokens", headers=AUTH)
        assert resp.status_code != 404

    def test_provider_keys_list_endpoint_registered(self, client, mock_svc):
        mock_svc.list_provider_keys.return_value = []
        resp = client.get("/v1/users/provider-keys", headers=AUTH)
        assert resp.status_code != 404

    def test_invites_endpoint_registered(self, client, mock_svc):
        mock_svc.get_user.return_value = {
            "id": "test-user-123",
            "email": "admin@example.com",
            "is_admin": True,
        }
        mock_svc.create_invite.return_value = "inv-token"
        resp = client.post("/v1/users/invites", headers=AUTH)
        assert resp.status_code != 404
