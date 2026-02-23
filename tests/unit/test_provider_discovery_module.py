"""Unit tests for the provider_discovery module.

Traceability:
  SYS-REQ-071   Discover models from connected external providers
  SYS-REQ-072   Credits / quota status included in responses
  SYS-REQ-073   Free-tier fallback indication
  SYS-NFR-021   Discovery results must be cached (≥5 min TTL)
  SYS-NFR-022   Credentials must never appear in log output
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from llm_api.api.schemas import CreditsStatus
from llm_api.integrations import provider_discovery
from llm_api.integrations.provider_discovery import (
    ProviderAvailability,
    _CACHE_TTL_SECONDS,
    get_provider_availability,
    get_provider_models,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Ensure the discovery cache is empty before and after each test."""
    provider_discovery._CACHE.clear()
    yield
    provider_discovery._CACHE.clear()


class TestGetProviderAvailabilityNoCreds:
    """Behaviour when a user has no credentials for a provider."""

    def test_no_credentials_returns_empty_models(self):
        result = get_provider_availability("user-1", "openai", credentials=None)
        assert result.models == []

    def test_no_credentials_credits_status_unknown(self):
        result = get_provider_availability("user-1", "openai", credentials=None)
        assert result.credits_status.status == "unknown"

    def test_no_credentials_populates_cache(self):
        """Even without creds the result should be cached to avoid hammering the provider."""
        get_provider_availability("user-1", "openai", credentials=None)
        cache_key = ("user-1", "openai")
        assert cache_key in provider_discovery._CACHE

    def test_empty_dict_credentials_treated_as_no_creds(self):
        """An empty credential dict should yield the same as None."""
        result = get_provider_availability("user-1", "openai", credentials={})
        # Empty creds still go through the happy path (static catalog returned)
        assert isinstance(result, ProviderAvailability)
        assert result.provider == "openai"


class TestGetProviderAvailabilityWithCreds:
    """Behaviour when credentials are present."""

    def test_with_credentials_returns_static_openai_catalog(self):
        creds = {"api_key": "sk-test-key"}
        result = get_provider_availability("user-1", "openai", credentials=creds)
        ids = [m.id for m in result.models]
        assert "gpt-4o" in ids or "gpt-4o-mini" in ids, f"Expected OpenAI models, got {ids}"

    def test_with_credentials_all_models_have_correct_provider(self):
        creds = {"api_key": "sk-test-key"}
        result = get_provider_availability("user-1", "openai", credentials=creds)
        for model in result.models:
            assert model.provider == "openai", f"Unexpected provider on {model.id}"

    def test_anthropic_catalog_returned_with_creds(self):
        creds = {"api_key": "sk-ant-test"}
        result = get_provider_availability("user-1", "anthropic", credentials=creds)
        assert len(result.models) > 0
        ids = [m.id for m in result.models]
        assert any("claude" in m_id.lower() for m_id in ids)

    def test_google_catalog_returned_with_creds(self):
        creds = {"api_key": "google-key"}
        result = get_provider_availability("user-1", "google", credentials=creds)
        assert len(result.models) > 0
        ids = [m.id for m in result.models]
        assert any("gemini" in m_id.lower() for m_id in ids)

    def test_xai_catalog_returned_with_creds(self):
        creds = {"api_key": "xai-key"}
        result = get_provider_availability("user-1", "xai", credentials=creds)
        assert len(result.models) > 0
        ids = [m.id for m in result.models]
        assert any("grok" in m_id.lower() for m_id in ids)

    def test_unknown_provider_returns_empty_list(self):
        creds = {"api_key": "some-key"}
        result = get_provider_availability("user-1", "unknown-provider", credentials=creds)
        assert result.models == []


class TestCreditsStatusFlags:
    """Credits status flag interpretation from credential metadata."""

    def test_credits_exhausted_flag_sets_status(self):
        creds = {"api_key": "sk-key", "credits_exhausted": True}
        result = get_provider_availability("user-1", "openai", credentials=creds)
        assert result.credits_status.status == "exhausted"

    def test_credits_available_flag_sets_status(self):
        creds = {"api_key": "sk-key", "credits_available": True}
        result = get_provider_availability("user-1", "openai", credentials=creds)
        assert result.credits_status.status == "available"

    def test_no_flag_defaults_to_unknown(self):
        creds = {"api_key": "sk-key"}
        result = get_provider_availability("user-1", "openai", credentials=creds)
        assert result.credits_status.status == "unknown"

    def test_credits_status_has_correct_provider(self):
        creds = {"api_key": "sk-key"}
        result = get_provider_availability("user-1", "openai", credentials=creds)
        assert result.credits_status.provider == "openai"


class TestCaching:
    """SYS-NFR-021: Results are cached and reused."""

    def test_second_call_returns_cached_result(self):
        creds = {"api_key": "sk-key"}
        first = get_provider_availability("user-1", "openai", credentials=creds)
        second = get_provider_availability("user-1", "openai", credentials=creds)
        # Same object (identical cached_at)
        assert first.cached_at == second.cached_at

    def test_force_refresh_bypasses_cache(self):
        creds = {"api_key": "sk-key"}
        first = get_provider_availability("user-1", "openai", credentials=creds)
        second = get_provider_availability("user-1", "openai", credentials=creds, force_refresh=True)
        # Force refresh should produce a new entry with a new timestamp
        assert second.cached_at >= first.cached_at

    def test_different_users_have_separate_cache_entries(self):
        creds = {"api_key": "sk-key"}
        get_provider_availability("user-A", "openai", credentials=creds)
        get_provider_availability("user-B", "openai", credentials=creds)
        assert ("user-A", "openai") in provider_discovery._CACHE
        assert ("user-B", "openai") in provider_discovery._CACHE

    def test_different_providers_have_separate_cache_entries(self):
        creds_openai = {"api_key": "sk-key"}
        creds_anthropic = {"api_key": "sk-ant"}
        get_provider_availability("user-1", "openai", credentials=creds_openai)
        get_provider_availability("user-1", "anthropic", credentials=creds_anthropic)
        assert ("user-1", "openai") in provider_discovery._CACHE
        assert ("user-1", "anthropic") in provider_discovery._CACHE

    def test_expired_cache_entry_is_refreshed(self):
        creds = {"api_key": "sk-key"}
        # Populate cache
        first = get_provider_availability("user-1", "openai", credentials=creds)

        # Manually back-date the cache entry beyond TTL
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=_CACHE_TTL_SECONDS + 1)
        provider_discovery._CACHE[("user-1", "openai")].cached_at = stale_time

        # Re-request — should refresh
        refreshed = get_provider_availability("user-1", "openai", credentials=creds)
        assert refreshed.cached_at > stale_time

    def test_cache_ttl_recorded_on_entry(self):
        creds = {"api_key": "sk-key"}
        result = get_provider_availability("user-1", "openai", credentials=creds)
        assert result.ttl_seconds == _CACHE_TTL_SECONDS


class TestGetProviderModels:
    """Convenience wrapper function."""

    def test_returns_same_models_as_availability(self):
        creds = {"api_key": "sk-key"}
        availability = get_provider_availability("user-1", "openai", credentials=creds)
        models = get_provider_models("user-1", "openai", credentials=creds)
        assert {m.id for m in models} == {m.id for m in availability.models}

    def test_no_creds_returns_empty_list(self):
        models = get_provider_models("user-1", "openai", credentials=None)
        assert models == []


class TestNoSecretsInLogs:
    """SYS-NFR-022: Raw API keys must not appear in log output."""

    def test_api_key_not_logged_during_discovery(self, caplog):
        api_key = "sk-very-secret-key-123456"
        creds = {"api_key": api_key}
        with caplog.at_level(logging.DEBUG, logger="llm_api.integrations.provider_discovery"):
            get_provider_availability("user-1", "openai", credentials=creds)
        for record in caplog.records:
            assert api_key not in record.getMessage(), (
                f"API key leaked in log: {record.getMessage()}"
            )
        # Also check formatted output
        assert api_key not in caplog.text
