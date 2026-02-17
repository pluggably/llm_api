from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from llm_api.adapters import (
    AnthropicAdapter,
    LocalAdapter,
    LocalTextAdapter,
    LocalImageAdapter,
    Local3DAdapter,
    OpenAIAdapter,
)
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


def _adapter_for_provider(
    provider: str,
    model_id: str,
    settings: Settings,
    model_path: Optional[str] = None,
    modality: str = "text",
    parameters: Optional[Dict[str, Any]] = None,
    provider_credentials: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Adapter:
    """Create an adapter for the given provider and modality."""
    supported = {"openai", "anthropic", "google", "azure", "xai", "local"}
    if provider not in supported:
        raise ProviderNotSupportedError(f"Unsupported provider: {provider}")

    if provider == "openai":
        user_key = (provider_credentials or {}).get("openai", {}).get("api_key")
        api_key = user_key or settings.openai_api_key
        if not api_key:
            raise ProviderNotConfiguredError(
                f"OpenAI API key not configured. Set LLM_API_OPENAI_API_KEY environment variable."
            )
        return OpenAIAdapter(
            model_id=model_id,
            api_key=api_key,
            base_url=settings.openai_base_url,
        )
    if provider == "anthropic":
        user_key = (provider_credentials or {}).get("anthropic", {}).get("api_key")
        api_key = user_key or settings.anthropic_api_key
        if not api_key:
            raise ProviderNotConfiguredError(
                f"Anthropic API key not configured. Set LLM_API_ANTHROPIC_API_KEY environment variable."
            )
        return AnthropicAdapter(
            model_id=model_id,
            api_key=api_key,
        )
    if provider == "google":
        user_key = (provider_credentials or {}).get("google", {}).get("api_key")
        api_key = user_key or settings.google_api_key
        if not api_key:
            raise ProviderNotConfiguredError(
                f"Google API key not configured. Set LLM_API_GOOGLE_API_KEY environment variable."
            )
        return GoogleAdapter(
            model_id=model_id,
            api_key=api_key,
        )
    if provider == "azure":
        azure_payload = (provider_credentials or {}).get("azure", {})
        api_key = azure_payload.get("api_key") or settings.azure_openai_api_key
        endpoint = azure_payload.get("endpoint") or settings.azure_openai_endpoint
        if not api_key or not endpoint:
            raise ProviderNotConfiguredError(
                f"Azure OpenAI not configured. Set LLM_API_AZURE_OPENAI_API_KEY and LLM_API_AZURE_OPENAI_ENDPOINT."
            )
        return AzureOpenAIAdapter(
            deployment=model_id,
            api_key=api_key,
            endpoint=endpoint,
            api_version=settings.azure_openai_api_version,
        )
    if provider == "xai":
        user_key = (provider_credentials or {}).get("xai", {}).get("api_key")
        api_key = user_key or settings.xai_api_key
        if not api_key:
            raise ProviderNotConfiguredError(
                f"xAI API key not configured. Set LLM_API_XAI_API_KEY environment variable."
            )
        return XAIAdapter(
            model_id=model_id,
            api_key=api_key,
            base_url=settings.xai_base_url,
        )
    
    # Local provider - extract HuggingFace token from user credentials
    hf_token = (provider_credentials or {}).get("huggingface", {}).get("api_key")

    if modality == "image":
        return LocalImageAdapter(
            model_path=model_path,
            model_id=model_id,
            modality=modality,
            parameters=parameters,
            hf_token=hf_token,
        )
    elif modality == "3d":
        return Local3DAdapter(
            model_path=model_path,
            model_id=model_id,
            modality=modality,
            parameters=parameters,
            hf_token=hf_token,
        )
    else:
        return LocalTextAdapter(
            model_path=model_path,
            model_id=model_id,
            modality=modality,
            parameters=parameters,
            hf_token=hf_token,
        )


def select_backend(
    model_id: str | None,
    registry: ModelRegistry,
    settings: Settings,
    modality: str = "text",
    provider_credentials: Optional[Dict[str, Dict[str, Any]]] = None,
) -> BackendSelection:
    """
    Select the appropriate backend for a model request.
    
    Supports multiple resolution strategies:
    1. Explicit provider prefix: "openai:gpt-4" or "anthropic:claude-3-opus"
    2. Well-known model patterns: "gpt-4" -> OpenAI, "claude-3" -> Anthropic
    3. Registry lookup: Check if model is registered
    4. Modality-appropriate default: Find a model matching the requested modality
    5. Default model fallback
    
    The modality parameter indicates the requested output type.
    For registered models, the model's own modality is used for adapter selection.
    """
    # If no model specified, try to find a suitable default for the modality
    if model_id is None:
        if modality == "image":
            model_id = settings.default_image_model
        elif modality == "3d":
            model_id = settings.default_3d_model
        elif modality != "text":
            # Try to find an available model for this modality
            default_for_modality = registry.get_default_for_modality(modality)
            if default_for_modality:
                model_id = default_for_modality
            else:
                raise ModelNotFoundError(
                    f"No {modality} model available. Please specify a model or download one."
                )
        else:
            model_id = settings.default_model

    # Strategy 1: Check for explicit provider prefix
    explicit_provider, raw_model_id = _parse_provider_prefix(model_id)

    if explicit_provider:
        # User explicitly specified provider
        adapter = _adapter_for_provider(
            explicit_provider,
            raw_model_id,
            settings,
            modality=modality,
            provider_credentials=provider_credentials,
        )
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

        # Use the model's registered modality for adapter selection
        # This ensures image models get image adapters, etc.
        # The model's modality takes precedence - clients don't need to specify it
        model_modality = model.modality

        adapter = _adapter_for_provider(
            model.provider or "local",
            model.id,
            settings,
            model_path=model.local_path,
            modality=model_modality,
            provider_credentials=provider_credentials,
        )
        return BackendSelection(model=model, adapter=adapter)

    # Strategy 3: Infer provider from well-known model patterns
    inferred_provider = _infer_provider_from_model(model_id)
    if inferred_provider:
        adapter = _adapter_for_provider(
            inferred_provider,
            model_id,
            settings,
            modality=modality,
        )
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
