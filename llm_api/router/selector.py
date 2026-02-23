from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

from llm_api.adapters import (
    AnthropicAdapter,
    HuggingFaceAdapter,
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
from llm_api.api.schemas import CreditsStatus, ModelInfo, SelectionInfo
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
    selection: Optional[SelectionInfo] = None
    credits_status: Optional[CreditsStatus] = None


COMMERCIAL_PROVIDERS = {"openai", "anthropic", "google", "azure", "xai", "deepseek", "huggingface"}

# Cheapest/free-tier fallback models per provider (ordered cheapest-first).
# On a 429 rate-limit the server tries each in order before falling back to local.
PROVIDER_TIER_FALLBACK: Dict[str, list[str]] = {
    "openai": ["gpt-4o-mini", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-5-haiku-20241022"],
    "google": ["gemini-1.5-flash", "gemini-1.5-flash-8b"],
    "xai": ["grok-2"],
    "deepseek": ["deepseek-chat"],
}


def _infer_modality_from_prompt(
    prompt: Optional[str],
    images: Optional[list[str]],
    mesh: Optional[str],
    fallback: str,
) -> str:
    # NOTE: images/mesh are *input* attachments (multimodal context), not
    # modality requests.  A user who sends images with modality="text" wants
    # the model to *analyse* the images, not generate new ones.  We infer
    # modality only from prompt keywords.
    if prompt:
        lower = prompt.lower()
        image_keywords = [
            r"\bimage\b",
            r"\bphoto\b",
            r"\bpicture\b",
            r"\bdraw\b",
            r"\billustration\b",
            r"\brender\b",
            r"\bart\b",
        ]
        mesh_keywords = [
            r"\b3d\b",
            r"\bmesh\b",
            r"\bobj\b",
            r"\bgltf\b",
            r"\bglb\b",
            r"\bmodel\b.*\b3d\b",
        ]
        if any(re.search(pattern, lower) for pattern in image_keywords):
            return "image"
        if any(re.search(pattern, lower) for pattern in mesh_keywords):
            return "3d"
    return fallback


def _matches_selection_mode(provider: Optional[str], selection_mode: str) -> bool:
    if selection_mode == "free_only":
        return provider not in COMMERCIAL_PROVIDERS
    if selection_mode == "commercial_only":
        return provider in COMMERCIAL_PROVIDERS
    return True


def _get_model_from_registry(registry: ModelRegistry, model_id: str) -> Optional[ModelInfo]:
    for model in registry.list_models():
        if model.id == model_id:
            return model
    return None


def _provider_for_model_id(
    model_id: str,
    registry: ModelRegistry,
) -> Optional[str]:
    explicit_provider, _ = _parse_provider_prefix(model_id)
    if explicit_provider:
        return explicit_provider
    model = _get_model_from_registry(registry, model_id)
    if model and model.provider:
        return model.provider
    inferred = _infer_provider_from_model(model_id)
    return inferred or "local"


def _model_id_matches_filter(
    model_id: str,
    registry: ModelRegistry,
    selection_mode: str,
) -> bool:
    provider = _provider_for_model_id(model_id, registry)
    return _matches_selection_mode(provider, selection_mode)


# Well-known model patterns for each provider
PROVIDER_MODEL_PATTERNS = {
    "openai": [
        r"^gpt-.*",
        r"^o1.*",
        r"^o3.*",
        r"^o4.*",
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
    "deepseek": [
        r"^deepseek-.*",
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
    supported = {"openai", "anthropic", "google", "azure", "xai", "deepseek", "huggingface", "local"}
    if provider not in supported:
        raise ProviderNotSupportedError(f"Unsupported provider: {provider}")

    creds_available = list((provider_credentials or {}).keys())
    logger.debug(
        "_adapter_for_provider: provider=%s model=%s modality=%s creds_available=%s",
        provider, model_id, modality, creds_available,
    )

    if provider == "openai":
        user_key = (provider_credentials or {}).get("openai", {}).get("api_key")
        api_key = user_key or settings.openai_api_key
        if not api_key:
            raise ProviderNotConfiguredError(
                f"OpenAI API key not configured. Set LLM_API_OPENAI_API_KEY environment variable."
            )
        logger.debug("openai adapter: using %s key", "user" if user_key else "settings")
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
        logger.debug("xai adapter: using %s key", "user" if user_key else "settings")
        return XAIAdapter(
            model_id=model_id,
            api_key=api_key,
            base_url=settings.xai_base_url,
        )
    if provider == "deepseek":
        user_key = (provider_credentials or {}).get("deepseek", {}).get("api_key")
        api_key = user_key or settings.deepseek_api_key
        if not api_key:
            raise ProviderNotConfiguredError(
                "DeepSeek API key not configured. Set LLM_API_DEEPSEEK_API_KEY environment variable."
            )
        logger.debug("deepseek adapter: using %s key", "user" if user_key else "settings")
        return OpenAIAdapter(
            model_id=model_id,
            api_key=api_key,
            base_url=settings.deepseek_base_url,
        )
    if provider == "huggingface":
        user_key = (provider_credentials or {}).get("huggingface", {}).get("api_key")
        api_key = user_key or settings.hf_token
        return HuggingFaceAdapter(
            model_id=model_id,
            api_key=api_key,
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


def select_provider_tier_fallback(
    failed_provider: str,
    failed_model_id: str,
    settings: Settings,
    provider_credentials: Optional[Dict[str, Dict[str, Any]]] = None,
    modality: str = "text",
    parameters: Optional[Dict[str, Any]] = None,
) -> BackendSelection:
    """Try cheaper-tier models from the same provider before falling back to local.

    Attempts each model in PROVIDER_TIER_FALLBACK[failed_provider] (skipping the
    failed model) and returns the first BackendSelection whose adapter can be
    constructed.  Raises ModelNotFoundError if none are available.
    """
    candidates = [
        m for m in PROVIDER_TIER_FALLBACK.get(failed_provider, [])
        if m != failed_model_id
    ]
    if not candidates:
        raise ModelNotFoundError(
            f"No tier fallback models defined for provider '{failed_provider}'"
        )

    last_exc: Exception = ModelNotFoundError("No candidates tried")
    for fallback_model_id in candidates:
        try:
            adapter = _adapter_for_provider(
                failed_provider,
                fallback_model_id,
                settings,
                modality=modality,
                provider_credentials=provider_credentials,
            )
            model_info = ModelInfo(
                id=fallback_model_id,
                name=fallback_model_id,
                version="latest",
                modality=modality,  # type: ignore[arg-type]
                provider=failed_provider,
                status="available",
            )
            selection_info = SelectionInfo(
                selected_model=fallback_model_id,
                selected_provider=failed_provider,
                fallback_used=True,
                fallback_reason="rate_limited_tier",
            )
            logger.debug(
                "select_provider_tier_fallback: using %s for provider %s (failed: %s)",
                fallback_model_id, failed_provider, failed_model_id,
            )
            return BackendSelection(model=model_info, adapter=adapter, selection=selection_info)
        except (ProviderNotConfiguredError, ProviderNotSupportedError) as e:
            last_exc = e
            logger.debug(
                "select_provider_tier_fallback: candidate %s unavailable: %s",
                fallback_model_id, e,
            )
    raise ModelNotFoundError(
        f"No working tier fallback for provider '{failed_provider}': {last_exc}"
    )


def select_backend(
    model_id: str | None,
    registry: ModelRegistry,
    settings: Settings,
    modality: str = "text",
    selection_mode: Optional[str] = None,
    prompt: Optional[str] = None,
    images: Optional[list[str]] = None,
    mesh: Optional[str] = None,
    provider: Optional[str] = None,
    provider_models: Optional[list[ModelInfo]] = None,
    credits_status: Optional[CreditsStatus] = None,
    provider_credentials: Optional[Dict[str, Dict[str, Any]]] = None,
    parameters: Optional[Dict[str, Any]] = None,
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
    selection_mode = selection_mode or (
        "model" if model_id and model_id != "auto" else "auto"
    )
    if model_id == "auto":
        model_id = None
    if model_id is not None and selection_mode != "model":
        selection_mode = "model"
    if selection_mode == "model" and not model_id:
        raise ModelNotFoundError(
            "Selection mode 'model' requires a specific model ID."
        )

    fallback_used = False
    fallback_reason: Optional[str] = None

    logger.debug(
        "select_backend: model_id=%r selection_mode=%s modality=%s provider=%s "
        "creds_providers=%s",
        model_id, selection_mode, modality, provider,
        list((provider_credentials or {}).keys()),
    )

    # If no model specified, try to find a suitable default for the modality
    if model_id is None:
        modality = _infer_modality_from_prompt(prompt, images, mesh, modality)

        if provider:
            provider_candidates = [
                m
                for m in (provider_models or [])
                if m.modality == modality and m.status == "available"
            ]
            if provider_candidates and (credits_status is None or credits_status.status != "exhausted"):
                model_id = provider_candidates[0].id
            else:
                # Fall back to free-tier/local models
                fallback_used = True
                fallback_reason = (
                    "credits_exhausted" if credits_status and credits_status.status == "exhausted" else "no_access"
                )
                candidates = [
                    m
                    for m in registry.list_models(modality=modality)
                    if m.status == "available"
                    and _matches_selection_mode(m.provider, "free_only")
                ]
                if candidates:
                    candidates.sort(
                        key=lambda m: m.last_used_at or datetime.min,
                        reverse=True,
                    )
                    model_id = candidates[0].id
                else:
                    raise ModelNotFoundError(
                        f"No {modality} model available for provider '{provider}'."
                    )
        else:
            default_id = registry.get_default_model_id(modality)

            if default_id and _model_id_matches_filter(default_id, registry, selection_mode):
                model_id = default_id
            else:
                candidates = [
                    m
                    for m in registry.list_models(modality=modality)
                    if m.status == "available"
                    and _matches_selection_mode(m.provider, selection_mode)
                ]
                if candidates:
                    candidates.sort(
                        key=lambda m: m.last_used_at or datetime.min,
                        reverse=True,
                    )
                    model_id = candidates[0].id
                else:
                    mode_suffix = (
                        f" (mode={selection_mode})" if selection_mode != "auto" else ""
                    )
                    raise ModelNotFoundError(
                        f"No {modality} model available{mode_suffix}. "
                        "Please specify a model or download one."
                    )

    # Strategy 1: Check for explicit provider prefix or provider override
    explicit_provider, raw_model_id = _parse_provider_prefix(model_id)
    if provider and not explicit_provider and not fallback_used:
        explicit_provider = provider
        raw_model_id = model_id

    if explicit_provider:
        logger.debug(
            "select_backend strategy1: explicit_provider=%s raw_model_id=%s",
            explicit_provider, raw_model_id,
        )
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
        selection = SelectionInfo(
            selected_model=raw_model_id,
            selected_provider=explicit_provider,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )
        return BackendSelection(model=model_info, adapter=adapter, selection=selection, credits_status=credits_status)

    # Strategy 2: Check registry first
    model = registry.get_model(model_id)
    logger.debug(
        "select_backend strategy2: registry lookup model_id=%s found=%s",
        model_id, model is not None,
    )
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
        selection = SelectionInfo(
            selected_model=model.id,
            selected_provider=model.provider,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )
        return BackendSelection(model=model, adapter=adapter, selection=selection, credits_status=credits_status)

    # Strategy 3: Infer provider from well-known model patterns
    inferred_provider = _infer_provider_from_model(model_id)
    logger.debug(
        "select_backend strategy3: model_id=%s inferred_provider=%s",
        model_id, inferred_provider,
    )
    if inferred_provider:
        adapter = _adapter_for_provider(
            inferred_provider,
            model_id,
            settings,
            modality=modality,
            provider_credentials=provider_credentials,
        )
        model_info = ModelInfo(
            id=model_id,
            name=model_id,
            version="latest",
            modality=modality,  # type: ignore[arg-type]
            provider=inferred_provider,
            status="available",
        )
        selection = SelectionInfo(
            selected_model=model_id,
            selected_provider=inferred_provider,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )
        logger.debug(
            "select_backend: strategy3 matched model=%s provider=%s",
            model_id, inferred_provider,
        )
        return BackendSelection(model=model_info, adapter=adapter, selection=selection, credits_status=credits_status)

    # Strategy 4: Model not found
    logger.warning(
        "select_backend: no strategy matched model_id=%r — raising ModelNotFoundError",
        model_id,
    )
    raise ModelNotFoundError(
        f"Model not found: {model_id}. "
        f"Use provider prefix (e.g., 'openai:{model_id}') or register the model first."
    )
