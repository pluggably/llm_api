from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"

    model_path: Path = Path("./models")
    max_disk_gb: float = 100.0

    api_key: str = Field(..., description="Required API key for requests")
    jwt_secret: Optional[str] = None
    local_only: bool = False

    artifact_store: Literal["local", "s3"] = "local"
    artifact_bucket: Optional[str] = None
    artifact_expiry_secs: int = 3600
    artifact_inline_threshold_kb: int = 256

    session_retention_minutes: int = 0

    metrics_enabled: bool = True

    persist_state: bool = False

    default_model: str = "local-text"
    default_temperature: float = 0.7
    default_max_tokens: int = 4096

    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_version: str = "2024-02-15-preview"

    xai_api_key: Optional[str] = None
    xai_base_url: str = "https://api.x.ai/v1"

    local_text_model_path: Optional[Path] = None
    local_image_model_id: str = "stabilityai/sd-turbo"
    local_3d_model_id: str = "shap-e"

    config_file: str = "config.yaml"

    model_config = SettingsConfigDict(env_prefix="LLM_API_", env_file=".env")


def _load_yaml(path: str) -> Dict[str, Any]:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    with file_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _flatten_yaml(data: Dict[str, Any]) -> Dict[str, Any]:
    server = data.get("server", {})
    storage = data.get("storage", {})
    auth = data.get("auth", {})
    artifacts = data.get("artifacts", {})
    defaults = data.get("defaults", {})
    providers = data.get("providers", {})
    openai = providers.get("openai", {})
    anthropic = providers.get("anthropic", {})
    google = providers.get("google", {})
    azure = providers.get("azure", {})
    xai = providers.get("xai", {})
    persistence = data.get("persistence", {})
    local = data.get("local", {})

    return {
        "host": server.get("host"),
        "port": server.get("port"),
        "log_level": server.get("log_level"),
        "model_path": storage.get("model_path"),
        "max_disk_gb": storage.get("max_disk_gb"),
        "api_key": auth.get("api_key"),
        "jwt_secret": auth.get("jwt_secret"),
        "local_only": auth.get("local_only"),
        "artifact_store": artifacts.get("store"),
        "artifact_bucket": artifacts.get("bucket"),
        "artifact_expiry_secs": artifacts.get("expiry_secs"),
        "default_model": defaults.get("model"),
        "default_max_tokens": defaults.get("max_tokens"),
        "default_temperature": defaults.get("temperature"),
        "openai_api_key": openai.get("api_key"),
        "openai_base_url": openai.get("base_url"),
        "anthropic_api_key": anthropic.get("api_key"),
        "google_api_key": google.get("api_key"),
        "azure_openai_api_key": azure.get("api_key"),
        "azure_openai_endpoint": azure.get("endpoint"),
        "azure_openai_api_version": azure.get("api_version"),
        "xai_api_key": xai.get("api_key"),
        "xai_base_url": xai.get("base_url"),
        "persist_state": persistence.get("enabled"),
        "local_text_model_path": local.get("text_model_path"),
        "local_image_model_id": local.get("image_model_id"),
        "local_3d_model_id": local.get("model_3d_id"),
    }


def _env_override(settings: Settings, env_map: Dict[str, str]) -> Settings:
    updates: Dict[str, Any] = {}
    for field_name, env_var in env_map.items():
        raw = os.getenv(env_var)
        if raw is None:
            continue
        updates[field_name] = raw
    if updates:
        return Settings(**{**settings.model_dump(), **updates})
    return settings


@lru_cache
def get_settings() -> Settings:
    config_file = os.getenv("LLM_API_CONFIG_FILE", "config.yaml")
    yaml_data = _load_yaml(config_file)
    flattened = {k: v for k, v in _flatten_yaml(yaml_data).items() if v is not None}

    # Only set api_key from env if present (to allow Pydantic to raise on missing)
    env_api_key = os.getenv("LLM_API_API_KEY")
    if "api_key" not in flattened and env_api_key is not None:
        flattened["api_key"] = env_api_key

    # Always pass flattened dict; Pydantic will raise if api_key is missing
    settings = Settings(**flattened)

    env_map = {
        "host": "LLM_API_HOST",
        "port": "LLM_API_PORT",
        "log_level": "LLM_API_LOG_LEVEL",
        "model_path": "LLM_API_MODEL_PATH",
        "max_disk_gb": "LLM_API_MAX_DISK_GB",
        "api_key": "LLM_API_API_KEY",
        "jwt_secret": "LLM_API_JWT_SECRET",
        "local_only": "LLM_API_LOCAL_ONLY",
        "artifact_store": "LLM_API_ARTIFACT_STORE",
        "artifact_bucket": "LLM_API_ARTIFACT_BUCKET",
        "artifact_expiry_secs": "LLM_API_ARTIFACT_EXPIRY_SECS",
        "artifact_inline_threshold_kb": "LLM_API_ARTIFACT_INLINE_THRESHOLD_KB",
        "metrics_enabled": "LLM_API_METRICS_ENABLED",
        "default_model": "LLM_API_DEFAULT_MODEL",
        "default_temperature": "LLM_API_DEFAULT_TEMPERATURE",
        "default_max_tokens": "LLM_API_DEFAULT_MAX_TOKENS",
        "openai_api_key": "LLM_API_OPENAI_API_KEY",
        "openai_base_url": "LLM_API_OPENAI_BASE_URL",
        "anthropic_api_key": "LLM_API_ANTHROPIC_API_KEY",
        "google_api_key": "LLM_API_GOOGLE_API_KEY",
        "azure_openai_api_key": "LLM_API_AZURE_OPENAI_API_KEY",
        "azure_openai_endpoint": "LLM_API_AZURE_OPENAI_ENDPOINT",
        "azure_openai_api_version": "LLM_API_AZURE_OPENAI_API_VERSION",
        "xai_api_key": "LLM_API_XAI_API_KEY",
        "xai_base_url": "LLM_API_XAI_BASE_URL",
        "persist_state": "LLM_API_PERSIST_STATE",
        "local_text_model_path": "LLM_API_LOCAL_TEXT_MODEL_PATH",
        "local_image_model_id": "LLM_API_LOCAL_IMAGE_MODEL_ID",
        "local_3d_model_id": "LLM_API_LOCAL_3D_MODEL_ID",
    }

    return _env_override(settings, env_map)
