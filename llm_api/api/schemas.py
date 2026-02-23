from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class Artifact(BaseModel):
    id: str
    type: Literal["image", "mesh"]
    url: str
    expires_at: datetime


class GenerateInput(BaseModel):
    prompt: Optional[str] = None
    images: Optional[List[str]] = None
    mesh: Optional[str] = None


class GenerateParameters(BaseModel):
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    format: Optional[str] = None


SelectionMode = Literal["auto", "free_only", "commercial_only", "model"]


class GenerateRequest(BaseModel):
    model: Optional[str] = None
    provider: Optional[str] = None
    session_id: Optional[str] = None
    state_tokens: Optional[Dict[str, Any]] = None
    modality: Literal["text", "image", "3d"]
    input: GenerateInput
    parameters: Optional[GenerateParameters] = None
    stream: bool = False
    selection_mode: Optional[SelectionMode] = None


class CreditsStatus(BaseModel):
    provider: str
    status: Literal["available", "exhausted", "rate_limited", "unknown"] = "unknown"
    remaining: Optional[float] = None
    reset_at: Optional[datetime] = None


class AvailabilityInfo(BaseModel):
    provider: str
    access: Literal["available", "locked", "unknown"] = "unknown"
    credits_status: Optional[CreditsStatus] = None


class SelectionInfo(BaseModel):
    selected_model: str
    selected_provider: Optional[str] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None


class GenerateOutput(BaseModel):
    text: Optional[str] = None
    images: Optional[List[str]] = None
    mesh: Optional[str] = None
    artifacts: Optional[List[Artifact]] = None


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GenerateResponse(BaseModel):
    request_id: str
    model: str
    modality: Literal["text", "image", "3d"]
    session_id: Optional[str] = None
    state_tokens: Optional[Dict[str, Any]] = None
    selection: Optional[SelectionInfo] = None
    credits_status: Optional[CreditsStatus] = None
    output: GenerateOutput
    usage: Usage
    warnings: Optional[List[str]] = None


class ModelCapabilities(BaseModel):
    max_context_tokens: Optional[int] = None
    output_formats: Optional[List[str]] = None
    hardware_requirements: Optional[List[str]] = None
    image_input_max_edge: Optional[int] = None
    image_input_max_pixels: Optional[int] = None
    image_input_formats: Optional[List[str]] = None


class ModelSource(BaseModel):
    type: Literal["huggingface", "url", "local"]
    uri: str


class ModelInfo(BaseModel):
    id: str
    name: str
    version: str
    modality: Literal["text", "image", "3d"]
    provider: Optional[str] = None
    capabilities: Optional[ModelCapabilities] = None
    source: Optional[ModelSource] = None
    size_bytes: Optional[int] = None
    local_path: Optional[str] = None
    last_used_at: Optional[datetime] = None
    is_default: Optional[bool] = None
    status: Literal["available", "downloading", "failed", "disabled", "evicted"] = "available"
    availability: Optional[AvailabilityInfo] = None


class ModelCatalog(BaseModel):
    models: List[ModelInfo]
    next_cursor: Optional[str] = None


class ProviderStatus(BaseModel):
    name: str
    configured: bool
    supported_modalities: List[Literal["text", "image", "3d"]]


class ProvidersResponse(BaseModel):
    providers: List[ProviderStatus]


class Session(BaseModel):
    id: str
    status: Literal["active", "closed"]
    title: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    message_count: int = 0
    messages: Optional[List["SessionMessageResponse"]] = None


class SessionMessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None


class SessionSummary(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    message_count: int = 0


class SessionList(BaseModel):
    sessions: List[SessionSummary]


class ModelDownloadSource(BaseModel):
    type: Literal["huggingface", "url", "local"]
    id: Optional[str] = None
    uri: Optional[str] = None


class ModelDownloadOptions(BaseModel):
    revision: Optional[str] = None
    sha256: Optional[str] = None
    allow_large: Optional[bool] = False
    install_local: Optional[bool] = True


class ModelDownloadRequest(BaseModel):
    model: ModelInfo
    source: ModelDownloadSource
    options: Optional[ModelDownloadOptions] = None


class DownloadJobStatus(BaseModel):
    job_id: str
    model_id: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    progress_pct: float = Field(ge=0, le=100)
    error: Optional[str] = None
    created_at: datetime


# User authentication schemas
class UserRegisterRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str
    invite_token: Optional[str] = None
    display_name: Optional[str] = None

    @model_validator(mode="after")
    def normalize_identifier(self) -> "UserRegisterRequest":
        identifier = (self.username or self.email or "").strip()
        if not identifier:
            raise ValueError("username or email is required")
        self.username = identifier
        self.email = identifier
        return self


class UserLoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def normalize_identifier(self) -> "UserLoginRequest":
        identifier = (self.username or self.email or "").strip()
        if not identifier:
            raise ValueError("username or email is required")
        self.username = identifier
        self.email = identifier
        return self


class UserLoginResponse(BaseModel):
    token: str
    user: Dict[str, Any]


class UserProfile(BaseModel):
    id: str
    username: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None
    preferred_model: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_identifier(self) -> "UserProfile":
        identifier = (self.username or self.email or "").strip()
        if not identifier:
            raise ValueError("username or email is required")
        self.username = identifier
        if self.email is None:
            self.email = identifier
        return self


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    preferred_model: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CreateTokenRequest(BaseModel):
    name: Optional[str] = None
    scopes: Optional[List[str]] = None
    expires_days: Optional[int] = None


class TokenInfo(BaseModel):
    id: str
    name: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    created_at: str
    last_used_at: Optional[str] = None
    expires_at: Optional[str] = None


class TokenCreatedResponse(BaseModel):
    token: str  # Only shown once
    info: TokenInfo


class ProviderKeyRequest(BaseModel):
    provider: str
    credential_type: Literal[
        "api_key",
        "endpoint_key",
        "oauth_token",
        "service_account",
    ] = "api_key"
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    oauth_token: Optional[str] = None
    service_account_json: Optional[str] = None


class ProviderKeyInfo(BaseModel):
    id: str
    provider: str
    credential_type: str
    masked_key: Optional[str] = None
    created_at: str


class ModelSearchResult(BaseModel):
    id: str
    name: str
    tags: List[str] = Field(default_factory=list)
    modality_hints: List[Literal["text", "image", "3d"]] = Field(default_factory=list)
    downloads: Optional[int] = None
    last_modified: Optional[datetime] = None


class ModelSearchResponse(BaseModel):
    results: List[ModelSearchResult]
    next_cursor: Optional[str] = None


# Model lifecycle schemas
class ModelRuntimeStatus(BaseModel):
    model_id: str
    runtime_status: Literal["unloaded", "loading", "loaded", "busy"]
    queue_depth: int = 0


class LoadedModelInfo(BaseModel):
    model_id: str
    loaded_at: str
    last_used_at: str
    is_pinned: bool
    memory_bytes: int
    is_busy: bool
    busy_count: int


class LoadedModelsResponse(BaseModel):
    models: List[LoadedModelInfo]


class LoadModelRequest(BaseModel):
    wait: bool = False
    use_fallback: bool = False
    fallback_model_id: Optional[str] = None


# Request queue schemas
class QueuePositionResponse(BaseModel):
    request_id: str
    status: Literal["pending", "queued", "running", "completed", "cancelled", "failed"]
    queue_position: Optional[int] = None


class CancelRequestResponse(BaseModel):
    request_id: str
    cancelled: bool
    status: str


# Regenerate schemas
class RegenerateRequest(BaseModel):
    model: Optional[str] = None
    parameters: Optional[GenerateParameters] = None
    stream: bool = False
    selection_mode: Optional[SelectionMode] = None
