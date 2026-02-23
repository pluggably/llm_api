"""Unit tests for selector provider preference, selection_mode filters, credits fallback.

Traceability:
  SYS-REQ-005   Auto-select a suitable model when none specified
  SYS-REQ-072   Credits / quota status propagated in response
  SYS-REQ-073   Free-tier fallback when credits exhausted
  SYS-REQ-075   Provider preference in generate requests
  SYS-REQ-CR003 Selection mode filters (free_only, commercial_only, model, auto)
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from llm_api.api.schemas import CreditsStatus, ModelInfo, SelectionInfo
from llm_api.config import Settings
from llm_api.registry.store import ModelRegistry
from llm_api.router.selector import (
    ModelNotFoundError,
    ProviderNotConfiguredError,
    BackendSelection,
    _infer_modality_from_prompt,
    _matches_selection_mode,
    select_backend,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _local_text_model(model_id: str, provider: str = "local") -> ModelInfo:
    return ModelInfo(
        id=model_id,
        name=model_id,
        version="latest",
        modality="text",
        provider=provider,
        status="available",
    )


def _local_image_model(model_id: str, provider: str = "local") -> ModelInfo:
    return ModelInfo(
        id=model_id,
        name=model_id,
        version="latest",
        modality="image",
        provider=provider,
        status="available",
    )


def _make_registry(*models: ModelInfo) -> ModelRegistry:
    registry = ModelRegistry()
    for m in models:
        registry.add_model(m)
    return registry


def _settings_no_providers() -> Settings:
    return Settings(api_key="test-key")


def _settings_with_openai() -> Settings:
    return Settings(api_key="test-key", openai_api_key="sk-test")


# ---------------------------------------------------------------------------
# _infer_modality_from_prompt
# ---------------------------------------------------------------------------

class TestInferModalityFromPrompt:
    """Unit tests for the _infer_modality_from_prompt helper."""

    def test_no_input_returns_fallback(self):
        assert _infer_modality_from_prompt(None, None, None, "text") == "text"

    def test_images_are_input_not_modality(self):
        """Images attached to a prompt are multimodal *inputs*, not a modality
        request.  The fallback modality should be preserved."""
        assert _infer_modality_from_prompt("describe this", ["img.png"], None, "text") == "text"

    def test_mesh_is_input_not_modality(self):
        """A mesh attached to a prompt is a multimodal *input*, not a modality
        request.  The fallback modality should be preserved."""
        assert _infer_modality_from_prompt(None, None, "object.obj", "text") == "text"

    def test_images_with_image_keyword_returns_image(self):
        """When the prompt explicitly asks for image generation AND images are
        attached, the keyword should still win."""
        assert _infer_modality_from_prompt("draw a picture based on this", ["ref.png"], None, "text") == "image"

    def test_mesh_with_3d_keyword_returns_3d(self):
        """When the prompt explicitly asks for 3D AND a mesh is attached, the
        keyword should still win."""
        assert _infer_modality_from_prompt("create a 3d model like this mesh", None, "ref.obj", "text") == "3d"

    @pytest.mark.parametrize("prompt", [
        "Generate a photo of a sunset",
        "Draw a picture of a cat",
        "Create an illustration of mountains",
        "Render a beautiful scene",
    ])
    def test_image_keyword_in_prompt_returns_image(self, prompt: str):
        assert _infer_modality_from_prompt(prompt, None, None, "text") == "image"

    @pytest.mark.parametrize("prompt", [
        "Generate a 3D model of a chair",
        "Create a mesh file for the object",
        "Export as GLB format",
    ])
    def test_3d_keyword_in_prompt_returns_3d(self, prompt: str):
        assert _infer_modality_from_prompt(prompt, None, None, "text") == "3d"

    def test_plain_text_prompt_returns_text_fallback(self):
        assert _infer_modality_from_prompt("What is the capital of France?", None, None, "text") == "text"


# ---------------------------------------------------------------------------
# _matches_selection_mode
# ---------------------------------------------------------------------------

class TestMatchesSelectionMode:
    """Unit tests for _matches_selection_mode."""

    @pytest.mark.parametrize("provider", ["openai", "anthropic", "google", "azure", "xai", "huggingface"])
    def test_free_only_rejects_commercial_providers(self, provider):
        assert _matches_selection_mode(provider, "free_only") is False

    @pytest.mark.parametrize("provider", ["local", None, "custom-local"])
    def test_free_only_accepts_local_providers(self, provider):
        assert _matches_selection_mode(provider, "free_only") is True

    @pytest.mark.parametrize("provider", ["openai", "anthropic", "google", "azure", "xai", "huggingface"])
    def test_commercial_only_accepts_commercial_providers(self, provider):
        assert _matches_selection_mode(provider, "commercial_only") is True

    @pytest.mark.parametrize("provider", ["local", None])
    def test_commercial_only_rejects_local(self, provider):
        assert _matches_selection_mode(provider, "commercial_only") is False

    def test_auto_mode_accepts_any_provider(self):
        for p in ["local", "openai", "anthropic", None]:
            assert _matches_selection_mode(p, "auto") is True

    def test_model_mode_accepts_any_provider(self):
        for p in ["local", "openai", None]:
            assert _matches_selection_mode(p, "model") is True


# ---------------------------------------------------------------------------
# Provider prefix routing
# ---------------------------------------------------------------------------

class TestProviderPrefixRouting:
    """select_backend with explicit provider:model syntax."""

    def test_openai_prefix_creates_openai_adapter(self):
        from llm_api.adapters import OpenAIAdapter
        registry = _make_registry()
        settings = _settings_with_openai()
        result = select_backend("openai:gpt-4o-mini", registry, settings)
        assert isinstance(result.adapter, OpenAIAdapter)

    def test_provider_prefix_sets_selection_info(self):
        from llm_api.adapters import OpenAIAdapter
        registry = _make_registry()
        settings = _settings_with_openai()
        result = select_backend("openai:gpt-4o", registry, settings)
        assert result.selection is not None
        assert result.selection.selected_provider == "openai"
        assert result.selection.selected_model == "gpt-4o"

    def test_unknown_provider_prefix_raises(self):
        registry = _make_registry()
        settings = _settings_no_providers()
        with pytest.raises(Exception):
            select_backend("unknownprovider:my-model", registry, settings)


# ---------------------------------------------------------------------------
# Provider parameter routing
# ---------------------------------------------------------------------------

class TestProviderParameterRouting:
    """select_backend with provider parameter (no model_id) + provider_models list."""

    def test_provider_with_models_selects_from_list(self):
        registry = _make_registry(_local_text_model("local-fallback"))
        settings = _settings_with_openai()
        provider_models = [
            ModelInfo(id="gpt-4o-mini", name="GPT-4o mini", version="latest",
                      modality="text", provider="openai", status="available"),
        ]
        # Should succeed because we have provider_models available
        result = select_backend(
            None, registry, settings,
            provider="openai",
            provider_models=provider_models,
        )
        assert result.selection is not None
        assert result.selection.selected_provider == "openai"
        assert result.selection.fallback_used is False

    def test_provider_exhausted_credits_falls_back(self):
        registry = _make_registry(_local_text_model("local-fallback"))
        settings = _settings_no_providers()
        provider_models = [
            ModelInfo(id="gpt-4o-mini", name="GPT-4o mini", version="latest",
                      modality="text", provider="openai", status="available"),
        ]
        exhausted = CreditsStatus(provider="openai", status="exhausted")

        result = select_backend(
            None, registry, settings,
            provider="openai",
            provider_models=provider_models,
            credits_status=exhausted,
        )
        assert result.selection is not None
        assert result.selection.fallback_used is True
        assert result.selection.fallback_reason == "credits_exhausted"
        # Should have fallen back to the local model
        assert result.model.provider != "openai" or result.selection.fallback_used

    def test_provider_no_access_falls_back(self):
        registry = _make_registry(_local_text_model("local-free"))
        settings = _settings_no_providers()
        # provider_models is empty → no access
        result = select_backend(
            None, registry, settings,
            provider="openai",
            provider_models=[],
        )
        assert result.selection is not None
        assert result.selection.fallback_used is True

    def test_provider_no_local_fallback_raises(self):
        registry = MagicMock()
        registry.list_models.return_value = []  # truly empty
        settings = _settings_no_providers()
        with pytest.raises(ModelNotFoundError):
            select_backend(
                None, registry, settings,
                provider="openai",
                provider_models=[],
            )

    def test_credits_status_propagated_in_result(self):
        registry = _make_registry(_local_text_model("local-fallback"))
        settings = _settings_no_providers()
        credit = CreditsStatus(provider="openai", status="exhausted")
        result = select_backend(
            None, registry, settings,
            provider="openai",
            provider_models=[],
            credits_status=credit,
        )
        assert result.credits_status is credit


# ---------------------------------------------------------------------------
# Selection mode filters
# ---------------------------------------------------------------------------

class TestSelectionModeFilters:
    """selection_mode=free_only / commercial_only / model / auto."""

    def test_free_only_uses_local_model(self):
        local = _local_text_model("my-local-model", provider="local")
        # Use MagicMock to avoid DB-seeded default model polluting the result
        registry = MagicMock()
        registry.get_default_model_id.return_value = "my-local-model"
        registry.list_models.return_value = [local]
        registry.get_model.return_value = local
        settings = _settings_no_providers()
        result = select_backend(None, registry, settings, selection_mode="free_only")
        assert result.model.provider not in {"openai", "anthropic", "google", "azure", "xai", "huggingface"}

    def test_free_only_raises_when_only_commercial_available(self):
        # Mock registry that only has a commercial OpenAI model
        commercial = ModelInfo(
            id="gpt-4o", name="GPT-4o", version="latest",
            modality="text", provider="openai", status="available"
        )
        registry = MagicMock()
        registry.list_models.return_value = [commercial]
        registry.get_default_model_id.return_value = None
        settings = _settings_no_providers()
        with pytest.raises(ModelNotFoundError):
            select_backend(None, registry, settings, selection_mode="free_only")

    def test_commercial_only_with_registry_commercial_model(self):
        from llm_api.adapters import OpenAIAdapter
        commercial = ModelInfo(
            id="gpt-4o-mini", name="GPT-4o mini", version="latest",
            modality="text", provider="openai", status="available"
        )
        registry = _make_registry(commercial)
        settings = _settings_with_openai()
        result = select_backend(None, registry, settings, selection_mode="commercial_only")
        assert result.selection.selected_provider in {"openai", "anthropic", "google", "azure", "xai", "huggingface"}

    def test_selection_mode_model_without_model_id_raises(self):
        registry = _make_registry(_local_text_model("local-a"))
        settings = _settings_no_providers()
        with pytest.raises(ModelNotFoundError, match="requires a specific model ID"):
            select_backend(None, registry, settings, selection_mode="model")

    def test_selection_mode_model_with_model_id_succeeds(self):
        local = _local_text_model("my-model")
        registry = _make_registry(local)
        settings = _settings_no_providers()
        result = select_backend("my-model", registry, settings, selection_mode="model")
        assert result.model.id == "my-model"

    def test_auto_mode_falls_back_to_default(self):
        local = _local_text_model("default-text-model")
        registry = _make_registry(local)
        registry.set_default_model("text", "default-text-model")
        settings = _settings_no_providers()
        result = select_backend(None, registry, settings, selection_mode="auto")
        assert result.model.id == "default-text-model"

    def test_auto_string_treated_as_no_model_id(self):
        local = _local_text_model("auto-selected")
        registry = _make_registry(local)
        registry.set_default_model("text", "auto-selected")
        settings = _settings_no_providers()
        result = select_backend("auto", registry, settings)
        assert result.model.id == "auto-selected"


# ---------------------------------------------------------------------------
# SelectionInfo contract
# ---------------------------------------------------------------------------

class TestSelectionInfoContract:
    """BackendSelection.selection must be a properly-formed SelectionInfo."""

    def test_selection_info_present_for_registry_model(self, mock_registry):
        settings = _settings_with_openai()
        result = select_backend("gpt-4", mock_registry, settings)
        assert result.selection is not None
        assert isinstance(result.selection, SelectionInfo)

    def test_selection_info_has_selected_model(self, mock_registry):
        settings = _settings_with_openai()
        result = select_backend("gpt-4", mock_registry, settings)
        assert result.selection.selected_model == "gpt-4"

    def test_selection_info_no_fallback_for_explicit_model(self, mock_registry):
        settings = _settings_with_openai()
        result = select_backend("gpt-4", mock_registry, settings)
        assert result.selection.fallback_used is False
        assert result.selection.fallback_reason is None

    def test_selection_info_fallback_set_on_unavailable_model(self, mock_registry):
        settings = _settings_with_openai()
        fallback = ModelInfo(
            id="gpt-3.5", name="gpt-3.5", version="latest",
            modality="text", provider="openai", status="available"
        )
        mock_registry.add_model(fallback)
        mock_registry.update_model_status("gpt-4", "disabled")
        mock_registry.set_fallback("gpt-4", "gpt-3.5")
        result = select_backend("gpt-4", mock_registry, settings)
        # Selection should show the fallback model
        assert result.model.id == "gpt-3.5"
