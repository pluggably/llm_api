from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import httpx

from llm_api.api.schemas import CreditsStatus, ModelInfo

logger = logging.getLogger(__name__)

_DISCOVERY_TIMEOUT = 10.0  # seconds


@dataclass
class ProviderAvailability:
    provider: str
    models: List[ModelInfo]
    credits_status: CreditsStatus
    cached_at: datetime
    ttl_seconds: int


_CACHE: Dict[Tuple[str, str], ProviderAvailability] = {}
_CACHE_TTL_SECONDS = 300
_QUOTA_EXHAUSTED_TTL_SECONDS = 3600  # don't retry exhausted providers for 1 hour
_RATE_LIMIT_BACKOFF_SECONDS = 60    # short back-off for transient rate limits


def _is_cache_valid(entry: ProviderAvailability) -> bool:
    return (datetime.now(timezone.utc) - entry.cached_at) < timedelta(seconds=entry.ttl_seconds)


# ---------------------------------------------------------------------------
# Balance / credits helpers (provider-specific)
# ---------------------------------------------------------------------------

def _check_deepseek_balance(api_key: str) -> CreditsStatus:
    """Query DeepSeek's /user/balance endpoint.

    Returns CreditsStatus with:
      - status="available"  when is_available=True and balance > 0
      - status="exhausted"  when is_available=False or balance = 0
      - status="unknown"    on any error
    """
    try:
        resp = httpx.get(
            "https://api.deepseek.com/user/balance",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_DISCOVERY_TIMEOUT,
        )
        if resp.status_code == 401:
            return CreditsStatus(provider="deepseek", status="exhausted")
        if resp.status_code != 200:
            return CreditsStatus(provider="deepseek", status="unknown")
        data = resp.json()
        is_available: bool = data.get("is_available", True)
        balance_infos: list = data.get("balance_infos", [])
        # Sum all available (topped-up) credits across currencies
        total_available = sum(
            float(bi.get("available_balance") or bi.get("topped_up_balance") or 0)
            for bi in balance_infos
        )
        if not is_available or total_available <= 0:
            logger.info("DeepSeek balance check: exhausted (is_available=%s, total=%.2f)",
                        is_available, total_available)
            return CreditsStatus(provider="deepseek", status="exhausted", remaining=0.0)
        logger.debug("DeepSeek balance check: available (total=%.2f)", total_available)
        return CreditsStatus(provider="deepseek", status="available", remaining=total_available)
    except Exception as exc:
        logger.warning("DeepSeek balance check failed: %s", exc)
        return CreditsStatus(provider="deepseek", status="unknown")


def get_cached_availability(user_id: str, provider: str) -> Optional[ProviderAvailability]:
    """Return the cached availability entry without triggering a new fetch."""
    entry = _CACHE.get((user_id, provider))
    if entry and _is_cache_valid(entry):
        return entry
    return None


def mark_provider_quota_exhausted(
    user_id: str,
    provider: str,
    ttl_seconds: int = _QUOTA_EXHAUSTED_TTL_SECONDS,
) -> None:
    """Record that a provider returned a quota-exhausted error for this user.

    If a valid cache entry exists its credits_status is updated in-place.  A
    fresh entry with no models (but exhausted status) is inserted otherwise.
    TTL defaults to 1 hour so we don't keep hammering an exhausted provider.
    """
    key = (user_id, provider)
    existing = _CACHE.get(key)
    if existing:
        existing.credits_status = CreditsStatus(provider=provider, status="exhausted")
        existing.ttl_seconds = ttl_seconds
        existing.cached_at = datetime.now(timezone.utc)
        logger.info("mark_provider_quota_exhausted: updated cache for user=%s provider=%s ttl=%ds",
                    user_id, provider, ttl_seconds)
    else:
        _CACHE[key] = ProviderAvailability(
            provider=provider,
            models=[],
            credits_status=CreditsStatus(provider=provider, status="exhausted"),
            cached_at=datetime.now(timezone.utc),
            ttl_seconds=ttl_seconds,
        )
        logger.info("mark_provider_quota_exhausted: created cache entry user=%s provider=%s ttl=%ds",
                    user_id, provider, ttl_seconds)


def mark_provider_rate_limited(
    user_id: str,
    provider: str,
    ttl_seconds: int = _RATE_LIMIT_BACKOFF_SECONDS,
) -> None:
    """Record a transient rate-limit (429 that is NOT quota exhaustion).

    Shorter TTL than quota exhaustion — just 60 seconds by default so the
    provider is retried again soon.
    """
    key = (user_id, provider)
    existing = _CACHE.get(key)
    if existing:
        existing.credits_status = CreditsStatus(provider=provider, status="rate_limited")
        existing.ttl_seconds = ttl_seconds
        existing.cached_at = datetime.now(timezone.utc)
    else:
        _CACHE[key] = ProviderAvailability(
            provider=provider,
            models=[],
            credits_status=CreditsStatus(provider=provider, status="rate_limited"),
            cached_at=datetime.now(timezone.utc),
            ttl_seconds=ttl_seconds,
        )
    logger.debug("mark_provider_rate_limited: user=%s provider=%s ttl=%ds",
                 user_id, provider, ttl_seconds)


# ---------------------------------------------------------------------------
# Providers with no public model-list endpoint: use a curated known-good list.
# ---------------------------------------------------------------------------

_ANTHROPIC_MODELS: List[ModelInfo] = [
    # Only confirmed real Anthropic API model IDs (date-versioned or stable aliases).
    # Anthropic does not expose a /v1/models endpoint; this list is maintained manually.
    # Do NOT add speculative IDs — they produce silent 400 errors at generation time.
    ModelInfo(id="claude-3-7-sonnet-20250219", name="Claude 3.7 Sonnet", version="latest", modality="text", provider="anthropic", status="available", is_default=False),
    ModelInfo(id="claude-3-5-sonnet-20241022", name="Claude 3.5 Sonnet", version="latest", modality="text", provider="anthropic", status="available", is_default=False),
    ModelInfo(id="claude-3-5-haiku-20241022", name="Claude 3.5 Haiku", version="latest", modality="text", provider="anthropic", status="available", is_default=False),
    ModelInfo(id="claude-3-opus-20240229", name="Claude 3 Opus", version="latest", modality="text", provider="anthropic", status="available", is_default=False),
]

# ---------------------------------------------------------------------------
# Live OpenAI / OpenAI-compatible discovery
# ---------------------------------------------------------------------------

_OPENAI_COMPAT_BASE_URLS: Dict[str, str] = {
    "xai": "https://api.x.ai",
    "deepseek": "https://api.deepseek.com",
}

_OPENAI_INCLUDE = re.compile(r"^(gpt-|o1-|o3-|o4-|chatgpt-|dall-e-)", re.IGNORECASE)
_OPENAI_EXCLUDE = re.compile(
    r"(whisper|tts|embedding|babbage|davinci|curie|ada|realtime|audio-|dall-e-2)",
    re.IGNORECASE,
)
_IMAGE_PATTERN = re.compile(r"^dall-e", re.IGNORECASE)


def _openai_id_to_info(model_id: str, provider: str) -> Optional[ModelInfo]:
    if not _OPENAI_INCLUDE.match(model_id):
        return None
    if _OPENAI_EXCLUDE.search(model_id):
        return None
    modality = "image" if _IMAGE_PATTERN.match(model_id) else "text"
    # Build a friendly display name
    name = model_id.replace("-", " ")
    name = re.sub(r"\bgpt\b", "GPT", name, flags=re.IGNORECASE)
    name = re.sub(r"\bdall e\b", "DALL·E", name, flags=re.IGNORECASE)
    return ModelInfo(
        id=model_id,
        name=name,
        version="latest",
        modality=modality,
        provider=provider,
        status="available",
        is_default=False,
    )


def _fetch_openai_models(api_key: str, provider: str = "openai") -> List[ModelInfo]:
    base = _OPENAI_COMPAT_BASE_URLS.get(provider, "https://api.openai.com")
    try:
        resp = httpx.get(
            f"{base}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_DISCOVERY_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Failed to list %s models: %s", provider, exc)
        return []

    results: List[ModelInfo] = []
    for item in data.get("data") or data.get("models") or []:
        model_id = (item.get("id") or "").strip()
        info = _openai_id_to_info(model_id, provider)
        if info:
            results.append(info)

    results.sort(key=lambda m: (len(m.id), m.id))
    logger.debug("Discovered %d %s models via API", len(results), provider)
    return results


def _fetch_xai_models(api_key: str) -> List[ModelInfo]:
    models = _fetch_openai_models(api_key, provider="xai")
    # xAI uses a different prefix; the generic filter may strip too much — include any
    if not models:
        return [
            ModelInfo(id="grok-3", name="Grok 3", version="latest", modality="text", provider="xai", status="available", is_default=False),
            ModelInfo(id="grok-3-mini", name="Grok 3 Mini", version="latest", modality="text", provider="xai", status="available", is_default=False),
            ModelInfo(id="grok-2", name="Grok 2", version="latest", modality="text", provider="xai", status="available", is_default=False),
        ]
    return models


def _fetch_openai_compat_raw(api_key: str, provider: str) -> List[ModelInfo]:
    """Fetch all models from an OpenAI-compatible endpoint without filtering."""
    base = _OPENAI_COMPAT_BASE_URLS.get(provider, "https://api.openai.com")
    try:
        resp = httpx.get(
            f"{base}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_DISCOVERY_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Failed to list %s models: %s", provider, exc)
        return []

    results: List[ModelInfo] = []
    for item in data.get("data") or data.get("models") or []:
        model_id = (item.get("id") or "").strip()
        if not model_id:
            continue
        results.append(ModelInfo(
            id=model_id,
            name=model_id.replace("-", " "),
            version="latest",
            modality="text",
            provider=provider,
            status="available",
            is_default=False,
        ))
    return results


def _fetch_deepseek_models(api_key: str) -> List[ModelInfo]:
    models = _fetch_openai_compat_raw(api_key, provider="deepseek")
    if not models:
        return [
            ModelInfo(id="deepseek-chat", name="DeepSeek Chat", version="latest", modality="text", provider="deepseek", status="available", is_default=False),
            ModelInfo(id="deepseek-reasoner", name="DeepSeek Reasoner", version="latest", modality="text", provider="deepseek", status="available", is_default=False),
        ]
    return models


# ---------------------------------------------------------------------------
# Google Generative AI discovery
# ---------------------------------------------------------------------------

def _fetch_google_models(api_key: str) -> List[ModelInfo]:
    try:
        resp = httpx.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": api_key},
            timeout=_DISCOVERY_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Failed to list google models: %s", exc)
        return []

    results: List[ModelInfo] = []
    for item in data.get("models") or []:
        if "generateContent" not in (item.get("supportedGenerationMethods") or []):
            continue
        raw = item.get("name") or ""
        model_id = raw.replace("models/", "")
        if not model_id.startswith("gemini"):
            continue
        display = item.get("displayName") or model_id
        results.append(ModelInfo(
            id=model_id,
            name=display,
            version="latest",
            modality="text",
            provider="google",
            status="available",
            is_default=False,
        ))

    results.sort(key=lambda m: (len(m.id), m.id))
    logger.debug("Discovered %d google models via API", len(results))
    return results


# ---------------------------------------------------------------------------
# Azure: deployment-specific, no list endpoint
# ---------------------------------------------------------------------------

def _fetch_azure_models(credentials: Dict) -> List[ModelInfo]:
    deployment = credentials.get("deployment") or credentials.get("api_key")
    endpoint = credentials.get("endpoint", "")
    if not deployment or not endpoint:
        return []
    return [ModelInfo(
        id=f"azure/{deployment}",
        name=f"Azure: {deployment}",
        version="latest",
        modality="text",
        provider="azure",
        status="available",
        is_default=False,
    )]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def _discover_models(provider: str, credentials: Dict) -> List[ModelInfo]:
    """Call the appropriate provider API to get a live model list."""
    api_key = str(credentials.get("api_key") or credentials.get("oauth_token") or "")

    if provider == "openai":
        return _fetch_openai_models(api_key) or _provider_model_catalog().get("openai", [])
    if provider == "anthropic":
        return list(_ANTHROPIC_MODELS)
    if provider == "google":
        return _fetch_google_models(api_key) or _provider_model_catalog().get("google", [])
    if provider == "xai":
        return _fetch_xai_models(api_key)
    if provider == "deepseek":
        return _fetch_deepseek_models(api_key)
    return []


# ---------------------------------------------------------------------------
# Static fallback catalog — shown as "locked" when no credentials are saved
# ---------------------------------------------------------------------------

def _provider_model_catalog() -> Dict[str, List[ModelInfo]]:
    """Minimal static catalog used when credentials are absent."""
    return {
        "openai": [
            ModelInfo(id="gpt-4o", name="GPT-4o", version="latest", modality="text", provider="openai", status="available", is_default=False),
            ModelInfo(id="gpt-4o-mini", name="GPT-4o mini", version="latest", modality="text", provider="openai", status="available", is_default=False),
            ModelInfo(id="o3", name="o3", version="latest", modality="text", provider="openai", status="available", is_default=False),
            ModelInfo(id="dall-e-3", name="DALL·E 3", version="latest", modality="image", provider="openai", status="available", is_default=False),
        ],
        "anthropic": [
            ModelInfo(id="claude-3-7-sonnet-20250219", name="Claude 3.7 Sonnet", version="latest", modality="text", provider="anthropic", status="available", is_default=False),
            ModelInfo(id="claude-3-5-sonnet-20241022", name="Claude 3.5 Sonnet", version="latest", modality="text", provider="anthropic", status="available", is_default=False),
            ModelInfo(id="claude-3-5-haiku-20241022", name="Claude 3.5 Haiku", version="latest", modality="text", provider="anthropic", status="available", is_default=False),
        ],
        "google": [
            ModelInfo(id="gemini-2.0-flash", name="Gemini 2.0 Flash", version="latest", modality="text", provider="google", status="available", is_default=False),
            ModelInfo(id="gemini-1.5-pro", name="Gemini 1.5 Pro", version="latest", modality="text", provider="google", status="available", is_default=False),
        ],
        "xai": [
            ModelInfo(id="grok-3", name="Grok 3", version="latest", modality="text", provider="xai", status="available", is_default=False),
            ModelInfo(id="grok-3-mini", name="Grok 3 Mini", version="latest", modality="text", provider="xai", status="available", is_default=False),
        ],
        "deepseek": [
            ModelInfo(id="deepseek-chat", name="DeepSeek Chat", version="latest", modality="text", provider="deepseek", status="available", is_default=False),
            ModelInfo(id="deepseek-reasoner", name="DeepSeek Reasoner", version="latest", modality="text", provider="deepseek", status="available", is_default=False),
        ],
    }


def get_provider_catalog_models(provider: str) -> List[ModelInfo]:
    """Return the static model catalog for a provider (no credentials required)."""
    return list(_provider_model_catalog().get(provider, []))


def get_provider_availability(
    user_id: str,
    provider: str,
    credentials: Optional[Dict],
    force_refresh: bool = False,
) -> ProviderAvailability:
    cache_key = (user_id, provider)
    cached = _CACHE.get(cache_key)
    if cached and not force_refresh and _is_cache_valid(cached):
        return cached

    if not credentials:
        entry = ProviderAvailability(
            provider=provider,
            models=[],
            credits_status=CreditsStatus(provider=provider, status="unknown"),
            cached_at=datetime.now(timezone.utc),
            ttl_seconds=_CACHE_TTL_SECONDS,
        )
        _CACHE[cache_key] = entry
        return entry

    models = _discover_models(provider, credentials)

    # --- Credits / balance check (best-effort, provider-specific) ---
    # DeepSeek exposes a proper balance endpoint; for all others we rely on
    # cached state written back from 429 error responses at request time.
    credits_status = CreditsStatus(provider=provider, status="unknown")
    if provider == "deepseek":
        api_key = str(credentials.get("api_key") or "")
        if api_key:
            credits_status = _check_deepseek_balance(api_key)
    elif isinstance(credentials, dict):
        # Preserve any previously-written exhausted/rate_limited status that is
        # still within its TTL (set by mark_provider_quota_exhausted / mark_provider_rate_limited).
        existing = _CACHE.get(cache_key)
        if existing and _is_cache_valid(existing) and existing.credits_status.status in ("exhausted", "rate_limited"):
            credits_status = existing.credits_status
            logger.debug(
                "get_provider_availability: preserving cached credits_status=%s for %s",
                credits_status.status, provider,
            )
        elif credentials.get("credits_exhausted") is True:
            credits_status.status = "exhausted"
        elif credentials.get("credits_available") is True:
            credits_status.status = "available"

    entry = ProviderAvailability(
        provider=provider,
        models=models,
        credits_status=credits_status,
        cached_at=datetime.now(timezone.utc),
        ttl_seconds=_CACHE_TTL_SECONDS,
    )
    _CACHE[cache_key] = entry
    logger.debug(
        "Provider discovery updated",
        extra={"provider": provider, "user_id": user_id, "models": len(models)},
    )
    return entry


def get_provider_models(
    user_id: str,
    provider: str,
    credentials: Optional[Dict],
    force_refresh: bool = False,
) -> List[ModelInfo]:
    availability = get_provider_availability(user_id, provider, credentials, force_refresh)
    return availability.models
