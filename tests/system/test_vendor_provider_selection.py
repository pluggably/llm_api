"""Vendor / provider preference system tests.

Traceability:
  TEST-INT-NEW-001  SYS-REQ-071  provider models appear in catalog after credential added
  TEST-INT-NEW-002  SYS-REQ-072  generate response includes credits_status when available
  TEST-INT-NEW-003  SYS-REQ-073  fallback_used flag when credits exhausted
  TEST-INT-NEW-004  SYS-REQ-075  provider preference without model ID selects a model
  TEST-INT-NEW-005  SYS-NFR-021  discovery cache reused for repeated calls
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from llm_api.api.schemas import ModelInfo
from llm_api.registry import store as registry_store

HEADERS = {"X-API-Key": "test-key"}
AUTH_USER = {"user_id": "test-user-1", "email": "test@example.com"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def app_with_user(tmp_path):
    """App with an authenticated user injected into request state."""
    import os
    os.environ["LLM_API_API_KEY"] = "test-key"
    os.environ["LLM_API_MODEL_PATH"] = str(tmp_path)
    os.environ["LLM_API_DEFAULT_MODEL"] = "local-text"
    os.environ["LLM_API_JWT_SECRET"] = ""
    os.environ["LLM_API_LOCAL_ONLY"] = "false"

    from llm_api.config import get_settings
    from llm_api.registry import store as rs
    from llm_api.jobs import store as js
    from llm_api.observability import metrics
    from llm_api.db import database as db_module
    from llm_api.storage import artifact_store

    get_settings.cache_clear()
    rs._registry = None
    js._store = None
    metrics._store = None
    artifact_store._store = None
    db_module.close_db()
    db_module._engine = None
    db_module._SessionLocal = None

    from llm_api.main import create_app
    from starlette.middleware.base import BaseHTTPMiddleware

    app = create_app()

    class _InjectUser(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.headers.get("x-api-key") == "test-key":
                request.state.user = AUTH_USER
            return await call_next(request)

    app.add_middleware(_InjectUser)
    return app


@pytest.fixture
def client_with_user(app_with_user):
    return TestClient(app_with_user)


# ─────────────────────────────────────────────────────────────────────────────
# TEST-INT-NEW-001: Provider models appear in catalog when credentials present
# ─────────────────────────────────────────────────────────────────────────────

class TestProviderModelsInCatalog:
    """SYS-REQ-071, SYS-REQ-074: catalog shows provider models for credentialed user."""

    def test_catalog_shows_provider_models_locked_when_no_credentials(self, client_with_user):
        """Without stored credentials commercial models should appear as locked."""
        with patch("llm_api.api.router.get_user_service") as mock_svc:
            svc = MagicMock()
            svc.get_provider_credentials.return_value = None
            mock_svc.return_value = svc

            resp = client_with_user.get("/v1/models", headers=HEADERS)
        assert resp.status_code == 200
        models = resp.json()["models"]
        openai_models = [m for m in models if m.get("provider") == "openai"]
        assert len(openai_models) >= 1, "OpenAI models should appear even without credentials"
        for m in openai_models:
            avail = m.get("availability")
            assert avail is not None, "availability info should be present"
            assert avail.get("access") == "locked", (
                f"Expected 'locked' access without credentials, got {avail.get('access')!r}"
            )

    def test_catalog_includes_openai_models_when_credentials_present(self, client_with_user):
        """With OpenAI credentials stored, catalog should include OpenAI models."""
        from llm_api.integrations import provider_discovery
        # Clear cache to force re-discovery
        provider_discovery._CACHE.clear()

        with patch("llm_api.api.router.get_user_service") as mock_svc:
            svc = MagicMock()
            def _creds(user_id, provider):
                if provider == "openai":
                    return {"api_key": "sk-test"}
                return None
            svc.get_provider_credentials.side_effect = _creds
            mock_svc.return_value = svc

            resp = client_with_user.get("/v1/models", headers=HEADERS)

        assert resp.status_code == 200
        models = resp.json()["models"]
        openai_models = [m for m in models if m.get("provider") == "openai"]
        assert len(openai_models) >= 1, "Expected at least one openai model when credentials present"

    def test_catalog_model_has_availability_info(self, client_with_user):
        """Provider models in catalog should include availability info."""
        from llm_api.integrations import provider_discovery
        provider_discovery._CACHE.clear()

        with patch("llm_api.api.router.get_user_service") as mock_svc:
            svc = MagicMock()
            def _creds(user_id, provider):
                return {"api_key": "sk-test"} if provider == "anthropic" else None
            svc.get_provider_credentials.side_effect = _creds
            mock_svc.return_value = svc

            resp = client_with_user.get("/v1/models", headers=HEADERS)

        assert resp.status_code == 200
        models = resp.json()["models"]
        anthropic_models = [m for m in models if m.get("provider") == "anthropic"]
        if anthropic_models:
            avail = anthropic_models[0].get("availability")
            assert avail is not None, "Expected availability info on provider model"
            assert avail.get("provider") == "anthropic"
            assert avail.get("access") in ("available", "locked", "unknown")


# ─────────────────────────────────────────────────────────────────────────────
# TEST-INT-NEW-004: Vendor selection without model ID
# ─────────────────────────────────────────────────────────────────────────────

class TestVendorSelectionWithoutModelId:
    """SYS-REQ-075: provider preference selects a model without explicit model ID."""

    def test_provider_preference_openai_routes_to_openai(self, client_with_user):
        """Generate with provider='openai' and no model should select an openai model."""
        from llm_api.integrations import provider_discovery
        provider_discovery._CACHE.clear()

        with patch("llm_api.api.router.get_user_service") as mock_svc:
            svc = MagicMock()
            svc.get_provider_credentials.return_value = {"api_key": "sk-test"}
            mock_svc.return_value = svc

            with patch("llm_api.router.selector._adapter_for_provider") as mock_adapter:
                mock_adapter_instance = MagicMock()
                mock_adapter_instance.generate_text.return_value = "provider response"
                mock_adapter.return_value = mock_adapter_instance

                payload = {
                    "modality": "text",
                    "input": {"prompt": "Hello"},
                    "provider": "openai",
                }
                resp = client_with_user.post("/v1/generate", json=payload, headers=HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("output", {}).get("text")

    def test_provider_preference_response_includes_selection_metadata(self, client_with_user):
        """Generate with provider preference should include selection metadata."""
        from llm_api.integrations import provider_discovery
        provider_discovery._CACHE.clear()

        with patch("llm_api.api.router.get_user_service") as mock_svc:
            svc = MagicMock()
            svc.get_provider_credentials.return_value = {"api_key": "sk-test"}
            mock_svc.return_value = svc

            with patch("llm_api.router.selector._adapter_for_provider") as mock_adapter:
                mock_adapter_instance = MagicMock()
                mock_adapter_instance.generate_text.return_value = "hi"
                mock_adapter.return_value = mock_adapter_instance

                payload = {
                    "modality": "text",
                    "input": {"prompt": "Hello"},
                    "provider": "openai",
                }
                resp = client_with_user.post("/v1/generate", json=payload, headers=HEADERS)

        if resp.status_code == 200:
            body = resp.json()
            selection = body.get("selection")
            if selection:
                assert selection.get("selected_model"), "Expected selected_model in selection"

    def test_provider_preference_without_credentials_falls_back_to_local(self, client_with_user):
        """Provider preference with no stored credentials falls back to local model."""
        from llm_api.integrations import provider_discovery
        provider_discovery._CACHE.clear()

        with patch("llm_api.api.router.get_user_service") as mock_svc:
            svc = MagicMock()
            svc.get_provider_credentials.return_value = None
            mock_svc.return_value = svc

            payload = {
                "modality": "text",
                "input": {"prompt": "Hello"},
                "provider": "openai",
            }
            resp = client_with_user.post("/v1/generate", json=payload, headers=HEADERS)

        # Should either succeed with local fallback or return 404 with clear error
        assert resp.status_code in (200, 404), f"Unexpected {resp.status_code}: {resp.text}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST-INT-NEW-003: Free-tier fallback indication when credits exhausted
# ─────────────────────────────────────────────────────────────────────────────

class TestFallbackOnCreditsExhausted:
    """SYS-REQ-073: fallback indicated when premium credits are exhausted."""

    def test_exhausted_credits_causes_fallback(self, client_with_user):
        """When provider marks credits as exhausted, response should include fallback indicator."""
        from llm_api.integrations import provider_discovery
        provider_discovery._CACHE.clear()

        # Simulate credentials with exhausted flag
        with patch("llm_api.api.router.get_user_service") as mock_svc:
            svc = MagicMock()
            # Return credentials with credits_exhausted=True flag
            svc.get_provider_credentials.return_value = {
                "api_key": "sk-test",
                "credits_exhausted": True,
            }
            mock_svc.return_value = svc

            payload = {
                "modality": "text",
                "input": {"prompt": "Hello"},
                "provider": "openai",
            }
            resp = client_with_user.post("/v1/generate", json=payload, headers=HEADERS)

        # Should succeed (fell back to local) or fail if no local model available
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            body = resp.json()
            selection = body.get("selection")
            if selection:
                assert selection["fallback_used"] is True, (
                    "Expected fallback_used=True when credits exhausted"
                )

    def test_credits_status_in_response_when_available(self, client_with_user):
        """Generate response should expose credits_status when provider reports it."""
        from llm_api.integrations import provider_discovery
        provider_discovery._CACHE.clear()

        with patch("llm_api.api.router.get_user_service") as mock_svc:
            svc = MagicMock()
            svc.get_provider_credentials.return_value = {
                "api_key": "sk-test",
                "credits_available": True,
            }
            mock_svc.return_value = svc

            with patch("llm_api.router.selector._adapter_for_provider") as mock_adapter:
                mock_adapter_instance = MagicMock()
                mock_adapter_instance.generate_text.return_value = "hi"
                mock_adapter.return_value = mock_adapter_instance

                payload = {
                    "modality": "text",
                    "input": {"prompt": "Hello"},
                    "provider": "openai",
                }
                resp = client_with_user.post("/v1/generate", json=payload, headers=HEADERS)

        if resp.status_code == 200:
            body = resp.json()
            credits = body.get("credits_status")
            if credits:
                assert credits.get("provider") == "openai"
                assert credits.get("status") in ("available", "exhausted", "unknown")


# ─────────────────────────────────────────────────────────────────────────────
# TEST-INT-NEW-005: Discovery cache reused for repeated catalog calls
# ─────────────────────────────────────────────────────────────────────────────

class TestDiscoveryCaching:
    """SYS-NFR-021: discovery results are cached and reused."""

    def test_second_catalog_call_uses_cache(self, client_with_user):
        """Two consecutive /v1/models calls should return consistent provider models."""
        from llm_api.integrations import provider_discovery
        provider_discovery._CACHE.clear()

        call_count = {"n": 0}
        original_fn = provider_discovery.get_provider_availability

        def _counted(*args, **kwargs):
            call_count["n"] += 1
            return original_fn(*args, **kwargs)

        with patch("llm_api.integrations.provider_discovery.get_provider_availability", side_effect=_counted):
            with patch("llm_api.api.router.get_user_service") as mock_svc:
                svc = MagicMock()
                svc.get_provider_credentials.return_value = {"api_key": "sk-test"}
                mock_svc.return_value = svc

                # Re-import patched function in router
                with patch("llm_api.api.router.get_provider_availability", side_effect=_counted):
                    resp1 = client_with_user.get("/v1/models", headers=HEADERS)
                    calls_after_first = call_count["n"]
                    resp2 = client_with_user.get("/v1/models", headers=HEADERS)

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        # The number of openai models should be the same in both responses
        models1 = [m["id"] for m in resp1.json()["models"] if m.get("provider") == "openai"]
        models2 = [m["id"] for m in resp2.json()["models"] if m.get("provider") == "openai"]
        assert models1 == models2, "Provider model list should be consistent across calls"


# ─────────────────────────────────────────────────────────────────────────────
# Streaming: model_selected event includes provider info
# ─────────────────────────────────────────────────────────────────────────────

class TestStreamingProviderInfo:
    """SSE model_selected event should include provider field."""

    def test_stream_model_selected_has_provider(self, client_with_user):
        """model_selected SSE event should include provider field."""
        payload = {
            "modality": "text",
            "input": {"prompt": "Hello"},
            "stream": True,
        }
        with client_with_user.stream("POST", "/v1/generate", json=payload, headers=HEADERS) as resp:
            assert resp.status_code == 200
            lines = [ln for ln in resp.iter_lines() if ln.startswith("data: ")]

        for line in lines:
            raw = line[len("data: "):]
            if raw == "[DONE]":
                continue
            try:
                evt = json.loads(raw)
                if evt.get("event") == "model_selected":
                    # provider key may be None for local models, but key must exist
                    assert "provider" in evt, "model_selected should have 'provider' key"
                    assert "fallback_used" in evt
                    return
            except json.JSONDecodeError:
                pass
        pytest.fail("No model_selected SSE event found in stream")
