from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class GenerateInput(BaseModel):
    prompt: Optional[str] = None
    images: Optional[List[str]] = None
    mesh: Optional[str] = None


class GenerateParameters(BaseModel):
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    format: Optional[str] = None


class GenerateRequest(BaseModel):
    model: Optional[str] = None
    session_id: Optional[str] = None
    state_tokens: Optional[Dict[str, Any]] = None
    modality: Literal["text", "image", "3d"]
    input: GenerateInput
    parameters: Optional[GenerateParameters] = None
    stream: bool = False


class GenerateOutput(BaseModel):
    text: Optional[str] = None
    images: Optional[List[str]] = None
    mesh: Optional[str] = None
    artifacts: Optional[List[Dict[str, Any]]] = None


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
    output: GenerateOutput
    usage: Usage


class ModelCapabilities(BaseModel):
    max_context_tokens: Optional[int] = None
    output_formats: Optional[List[str]] = None
    hardware_requirements: Optional[List[str]] = None


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


class ModelCatalog(BaseModel):
    models: List[ModelInfo]
    next_cursor: Optional[str] = None


class ProviderStatus(BaseModel):
    name: str
    configured: bool
    supported_modalities: List[Literal["text", "image", "3d"]]


class ProvidersResponse(BaseModel):
    providers: List[ProviderStatus]


class ModelDownloadSource(BaseModel):
    type: Literal["huggingface", "url", "local"]
    id: Optional[str] = None
    uri: Optional[str] = None


class ModelDownloadOptions(BaseModel):
    revision: Optional[str] = None
    sha256: Optional[str] = None
    allow_large: Optional[bool] = None


class ModelDownloadRequest(BaseModel):
    model: Dict[str, Any]
    source: ModelDownloadSource
    options: Optional[ModelDownloadOptions] = None


class Session(BaseModel):
    id: str
    status: Literal["active", "closed"]
    created_at: datetime
    last_used_at: Optional[datetime] = None


class SessionList(BaseModel):
    sessions: List[Session]
