from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

from llm_api.adapters import AnthropicAdapter, LocalAdapter, OpenAIAdapter
from llm_api.adapters.base import Adapter
from llm_api.adapters.google import GoogleAdapter
from llm_api.adapters.azure_openai import AzureOpenAIAdapter
from llm_api.adapters.xai import XAIAdapter
from llm_api.api.schemas import ModelInfo
from llm_api.config import Settings
from llm_api.registry.store import ModelRegistry


class ModelNotFoundError(Exception):
    pass


class ProviderNotSupportedError(Exception):
    pass


class ProviderNotConfiguredError(Exception):
    pass


@dataclass
class BackendSelection:
    model: ModelInfo
    adapter: Adapter


# Well-known model patterns for each provider
PROVIDER_MODEL_PATTERNS = {
    "openai": [
        r"^gpt-4.*",
        r"^gpt-3\.5.*",
        r"^o1.*",
        r"^o3.*",
        r"^chatgpt.*",
        r"^text-davinci.*",
        r"^dall-e.*",
        r"^whisper.*",
        r"^tts.*",
    ],
    "anthropic": [
        r"^claude-3.*",
        r"^claude-2.*",
        r"^claude-instant.*",
        r"^claude-.*",
    ],
    "google": [
        r"^gemini-.*",
        r"^palm-.*",
        r"^gemma-.*",
    ],
    "xai": [
        r"^grok-.*",
    ],
}


def _infer_provider_from_model(model_id: str) -> Optional[str]:
    """Infer provider from well-known model ID patterns."""
    for provider, patterns in PROVIDER_MODEL_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, model_id, re.IGNORECASE):
                return provider
    return None


def _parse_provider_prefix(model_id: str) -> Tuple[Optional[str], str]:
    """Parse provider:model format. Returns (provider, model_id)."""
    if ":" in model_id:
        parts = model_id.split(":", 1)
        return parts[0].lower(), parts[1]
    return None, model_id


def _adapter_for_provider(provider: str, model_id: str, settings: Settings, model_path: Optional[str] = None) -> Adapter:
    """Create an adapter for the given provider."""
    supported = {"openai", "anthropic", "google", "azure", "xai", "local"}
    if provider not in supported:
        raise ProviderNotSupportedError(f"Unsupported provider: {provider}")

    if provider == "openai":
        if not settings.openai_api_key:
            raise ProviderNotConfiguredError(
                f"OpenAI API key not configured. Set LLM_API_OPENAI_API_KEY environment variable."
            )
        return OpenAIAdapter(
            model_id=model_id,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ProviderNotConfiguredError(
                f"Anthropic API key not configured. Set LLM_API_ANTHROPIC_API_KEY environment variable."
            )
        return AnthropicAdapter(
            model_id=model_id,
            api_key=settings.anthropic_api_key,
        )
    if provider == "google":
        if not settings.google_api_key:
            raise ProviderNotConfiguredError(
                f"Google API key not configured. Set LLM_API_GOOGLE_API_KEY environment variable."
            )
        return GoogleAdapter(
            model_id=model_id,
            api_key=settings.google_api_key,
        )
    if provider == "azure":
        if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
            raise ProviderNotConfiguredError(
                f"Azure OpenAI not configured. Set LLM_API_AZURE_OPENAI_API_KEY and LLM_API_AZURE_OPENAI_ENDPOINT."
            )
        return AzureOpenAIAdapter(
            deployment=model_id,
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
    if provider == "xai":
        if not settings.xai_api_key:
            raise ProviderNotConfiguredError(
                f"xAI API key not configured. Set LLM_API_XAI_API_KEY environment variable."
            )
        return XAIAdapter(
            model_id=model_id,
            api_key=settings.xai_api_key,
            base_url=settings.xai_base_url,
        )
    return LocalAdapter(model_path=model_path)


def select_backend(
    model_id: str | None,
    registry: ModelRegistry,
    settings: Settings,
    modality: str = "text",
) -> BackendSelection:
    """
    Select the appropriate backend for a model request.
    
    Supports multiple resolution strategies:
    1. Explicit provider prefix: "openai:gpt-4" or "anthropic:claude-3-opus"
    2. Well-known model patterns: "gpt-4" -> OpenAI, "claude-3" -> Anthropic
    3. Registry lookup: Check if model is registered
    4. Default model fallback
    """
    model_id = model_id or settings.default_model

    # Strategy 1: Check for explicit provider prefix
    explicit_provider, raw_model_id = _parse_provider_prefix(model_id)

    if explicit_provider:
        # User explicitly specified provider
        adapter = _adapter_for_provider(explicit_provider, raw_model_id, settings)
        model_info = ModelInfo(
            id=raw_model_id,
            name=raw_model_id,
            version="latest",
            modality=modality,  # type: ignore[arg-type]
            provider=explicit_provider,
            status="available",
        )
        return BackendSelection(model=model_info, adapter=adapter)

    # Strategy 2: Check registry first
    model = registry.get_model(model_id)
    if model:
        if model.status != "available":
            fallback_id = registry.get_fallback(model_id)
            if fallback_id:
                fallback = registry.get_model(fallback_id)
                if fallback and fallback.status == "available":
                    model = fallback
                else:
                    raise ModelNotFoundError(f"Fallback model not available: {fallback_id}")
            else:
                raise ModelNotFoundError(f"Model not available: {model_id} (status: {model.status})")

        adapter = _adapter_for_provider(
            model.provider or "local",
            model.id,
            settings,
            model_path=model.local_path,
        )
        return BackendSelection(model=model, adapter=adapter)

    # Strategy 3: Infer provider from well-known model patterns
    inferred_provider = _infer_provider_from_model(model_id)
    if inferred_provider:
        adapter = _adapter_for_provider(inferred_provider, model_id, settings)
        model_info = ModelInfo(
            id=model_id,
            name=model_id,
            version="latest",
            modality=modality,  # type: ignore[arg-type]
            provider=inferred_provider,
            status="available",
        )
        return BackendSelection(model=model_info, adapter=adapter)

    # Strategy 4: Model not found
    raise ModelNotFoundError(
        f"Model not found: {model_id}. "
        f"Use provider prefix (e.g., 'openai:{model_id}') or register the model first."
    )
