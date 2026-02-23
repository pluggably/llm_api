"""TEST-UNIT-002: Model selection logic
Traceability: SYS-REQ-011
"""
import pytest

from llm_api.config import Settings
from llm_api.router.selector import (
    ModelNotFoundError,
    ProviderNotConfiguredError,
    select_backend,
)
from llm_api.registry.store import ModelRegistry
from llm_api.api.schemas import ModelInfo
from llm_api.adapters import OpenAIAdapter, LocalAdapter


class TestModelSelectionLogic:
    """Unit tests for model routing and selection."""

    def test_routes_to_openai_for_gpt_model(self, mock_registry):
        """Test that gpt-4 routes to OpenAI when API key is configured."""
        settings = Settings(api_key="test-key", openai_api_key="sk-test-key")
        selection = select_backend("gpt-4", mock_registry, settings)
        assert isinstance(selection.adapter, OpenAIAdapter)

    def test_routes_to_local_for_oss_model(self, mock_registry):
        """Test that local models route to LocalAdapter."""
        settings = Settings(api_key="test-key")
        selection = select_backend("deepseek-r1", mock_registry, settings)
        assert isinstance(selection.adapter, LocalAdapter)

    def test_fallback_when_primary_unavailable(self, mock_registry):
        """Test fallback to alternate model when primary is disabled."""
        settings = Settings(api_key="test-key", openai_api_key="sk-test-key")
        fallback = ModelInfo(
            id="gpt-3.5",
            name="gpt-3.5",
            version="latest",
            modality="text",
            provider="openai",
        )
        mock_registry.add_model(fallback)
        mock_registry.update_model_status("gpt-4", "disabled")
        mock_registry.set_fallback("gpt-4", "gpt-3.5")
        selection = select_backend("gpt-4", mock_registry, settings)
        assert selection.model.id == "gpt-3.5"

    def test_raises_on_unknown_model(self, mock_registry):
        """Test that unknown models raise ModelNotFoundError."""
        settings = Settings(api_key="test-key")
        with pytest.raises(ModelNotFoundError):
            select_backend("unknown-model", mock_registry, settings)

    def test_uses_default_when_no_model_specified(self, mock_registry):
        """Test that default model is used when none specified."""
        settings = Settings(api_key="test-key", openai_api_key="sk-test-key", default_model="gpt-4")
        # Override get_default_model_id to avoid DB-seeded defaults
        mock_registry.get_default_model_id = lambda modality: "gpt-4"
        selection = select_backend(None, mock_registry, settings)
        assert selection.model.id == "gpt-4"

    def test_provider_not_configured_raises_error(self, mock_registry, monkeypatch):
        """Test that missing API key raises ProviderNotConfiguredError."""
        # Explicitly unset env var so .env doesn't leak a real key
        monkeypatch.delenv("LLM_API_OPENAI_API_KEY", raising=False)
        settings = Settings(api_key="test-key", openai_api_key=None)
        with pytest.raises(ProviderNotConfiguredError) as exc_info:
            select_backend("gpt-4", mock_registry, settings)
        assert "OpenAI API key not configured" in str(exc_info.value)
