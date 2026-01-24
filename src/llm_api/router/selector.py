from __future__ import annotations

from dataclasses import dataclass

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


@dataclass
class BackendSelection:
    model: ModelInfo
    adapter: Adapter


def _adapter_for_provider(provider: str, model_id: str, settings: Settings) -> Adapter:
    supported = {"openai", "anthropic", "google", "azure", "xai", "local"}
    if provider not in supported:
        raise ProviderNotSupportedError(f"Unsupported provider: {provider}")
    if provider == "openai":
        return OpenAIAdapter(
            model_id=model_id,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    if provider == "anthropic":
        return AnthropicAdapter(
            model_id=model_id,
            api_key=settings.anthropic_api_key,
        )
    if provider == "google":
        return GoogleAdapter(
            model_id=model_id,
            api_key=settings.google_api_key,
        )
    if provider == "azure":
        return AzureOpenAIAdapter(
            deployment=model_id,
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
    if provider == "xai":
        return XAIAdapter(
            model_id=model_id,
            api_key=settings.xai_api_key,
            base_url=settings.xai_base_url,
        )
    return LocalAdapter()


def select_backend(model_id: str | None, registry: ModelRegistry, settings: Settings) -> BackendSelection:
    model_id = model_id or settings.default_model
    model = registry.get_model(model_id)
    if not model:
        raise ModelNotFoundError(f"Model not found: {model_id}")

    if model.status != "available":
        fallback_id = registry.get_fallback(model_id)
        if fallback_id:
            fallback = registry.get_model(fallback_id)
            if fallback and fallback.status == "available":
                model = fallback
            else:
                raise ModelNotFoundError(f"Fallback model not available: {fallback_id}")
        else:
            raise ModelNotFoundError(f"Model not available: {model_id}")

    adapter = _adapter_for_provider(model.provider or "local", model.id, settings)
    return BackendSelection(model=model, adapter=adapter)
