from __future__ import annotations

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
import httpx
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse

from llm_api.api.schemas import (
    GenerateRequest,
    GenerateResponse,
    GenerateOutput,
    ModelCatalog,
    ModelDownloadRequest,
    ModelSearchResponse,
    ModelSearchResult,
    Usage,
    ModelInfo,
    ProvidersResponse,
    ProviderStatus,
    Session,
    SessionList,
    UpdateSessionRequest,
)
from llm_api.auth import require_api_key
from llm_api.config import get_settings
from llm_api.jobs import get_job_store
from llm_api.jobs.downloader import DownloadService
from llm_api.registry import get_registry
from llm_api.storage import encode_inline, get_artifact_store
from llm_api.router.selector import (
    ModelNotFoundError,
    ProviderNotSupportedError,
    ProviderNotConfiguredError,
    select_backend,
)
from llm_api.adapters import ProviderError, map_provider_error
from llm_api.sessions import get_session_store


api_router = APIRouter()


def _build_usage(prompt: str | None, output_text: str | None) -> Usage:
    prompt_tokens = len((prompt or "").split())
    completion_tokens = len((output_text or "").split())
    return Usage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )


def _artifact_inline_threshold_bytes() -> int:
    settings = get_settings()
    return settings.artifact_inline_threshold_kb * 1024


@api_router.post("/v1/generate", dependencies=[Depends(require_api_key)], response_model=None)
async def generate(request: GenerateRequest) -> JSONResponse | StreamingResponse:
    settings = get_settings()
    registry = get_registry()
    session_store = get_session_store()

    model_id = request.model
    session_id = request.session_id
    session = None
    if session_id:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        if session.status != "active":
            raise HTTPException(status_code=400, detail="Session is closed")

    effective_state_tokens = request.state_tokens
    if session and effective_state_tokens is None:
        effective_state_tokens = session.state_tokens

    try:
        selection = select_backend(model_id, registry, settings, modality=request.modality)
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderNotSupportedError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "unsupported_provider", "message": str(exc)},
        ) from exc
    except ProviderNotConfiguredError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "provider_not_configured", "message": str(exc)},
        ) from exc

    model_id = selection.model.id

    if request.stream:
        if request.modality != "text":
            raise HTTPException(status_code=400, detail="Streaming only supported for text")

        async def event_stream() -> AsyncGenerator[str, None]:
            try:
                output_text = selection.adapter.generate_text(request.input.prompt or "")
            except ProviderError as exc:
                error = map_provider_error(exc)
                payload = json.dumps({"error": {"code": error.code, "message": error.message}})
                yield f"data: {payload}\n\n"
                return

            payload = json.dumps({"choices": [{"delta": {"content": output_text}}]})
            yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"

        if session:
            session_store.append_message(
                session_id,
                request.modality,
                request.input.model_dump(mode="json"),
                {"stream": True},
                effective_state_tokens,
            )
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    request_id = str(uuid.uuid4())

    try:
        if request.modality == "text":
            output_text = selection.adapter.generate_text(request.input.prompt or "")
            output = GenerateOutput(text=output_text)
            usage = _build_usage(request.input.prompt, output_text)
        elif request.modality == "image":
            content = selection.adapter.generate_image(request.input.prompt or "")
            artifacts = []
            if len(content) > _artifact_inline_threshold_bytes():
                artifact = get_artifact_store().create_artifact(content, "image")
                artifacts.append(artifact)
                output = GenerateOutput(artifacts=artifacts)
            else:
                output = GenerateOutput(images=[encode_inline(content)])
            usage = Usage()
        else:
            content = selection.adapter.generate_3d(request.input.prompt or "")
            artifacts = []
            if len(content) > _artifact_inline_threshold_bytes():
                artifact = get_artifact_store().create_artifact(content, "mesh")
                artifacts.append(artifact)
                output = GenerateOutput(artifacts=artifacts)
            else:
                output = GenerateOutput(mesh=encode_inline(content))
            usage = Usage()
    except ProviderError as exc:
        error = map_provider_error(exc)
        raise HTTPException(
            status_code=error.status_code,
            detail={"code": error.code, "message": error.message},
        ) from exc

    response = GenerateResponse(
        request_id=request_id,
        model=model_id,
        modality=request.modality,
        session_id=session_id,
        state_tokens=effective_state_tokens,
        output=output,
        usage=usage,
    )
    if session:
        session_store.append_message(
            session_id,
            request.modality,
            request.input.model_dump(mode="json"),
            jsonable_encoder(output),
            effective_state_tokens,
        )
    return JSONResponse(jsonable_encoder(response))


@api_router.post("/v1/sessions", dependencies=[Depends(require_api_key)])
async def create_session(request: UpdateSessionRequest | None = None) -> JSONResponse:
    session_store = get_session_store()
    session = session_store.create_session(title=request.title if request else None)
    return JSONResponse(jsonable_encoder(session.to_public()), status_code=201)


@api_router.get("/v1/sessions", dependencies=[Depends(require_api_key)])
async def list_sessions() -> JSONResponse:
    session_store = get_session_store()
    sessions = session_store.list_sessions()
    return JSONResponse(jsonable_encoder(SessionList(sessions=sessions)))


@api_router.get("/v1/sessions/{session_id}", dependencies=[Depends(require_api_key)])
async def get_session(session_id: str) -> JSONResponse:
    session_store = get_session_store()
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return JSONResponse(jsonable_encoder(session.to_public(include_messages=True)))


@api_router.put("/v1/sessions/{session_id}", dependencies=[Depends(require_api_key)])
async def update_session(session_id: str, request: UpdateSessionRequest) -> JSONResponse:
    session_store = get_session_store()
    session = session_store.update_session(session_id, title=request.title)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return JSONResponse(jsonable_encoder(session.to_public()))


@api_router.delete("/v1/sessions/{session_id}", dependencies=[Depends(require_api_key)])
async def close_session(session_id: str) -> JSONResponse:
    session_store = get_session_store()
    session = session_store.close_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return JSONResponse(jsonable_encoder(session.to_public()))


@api_router.post("/v1/sessions/{session_id}/reset", dependencies=[Depends(require_api_key)])
async def reset_session(session_id: str) -> JSONResponse:
    session_store = get_session_store()
    session = session_store.reset_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return JSONResponse(jsonable_encoder(session.to_public()))


@api_router.post("/v1/sessions/{session_id}/generate", dependencies=[Depends(require_api_key)], response_model=None)
async def generate_with_session(session_id: str, request: GenerateRequest) -> JSONResponse | StreamingResponse:
    session_request = request.model_copy(update={"session_id": session_id})
    return await generate(session_request)


@api_router.get("/v1/models", dependencies=[Depends(require_api_key)])
async def list_models(modality: str | None = None, limit: int | None = None, cursor: str | None = None) -> JSONResponse:
    registry = get_registry()
    models = registry.list_models(modality=modality)
    if limit:
        start = int(cursor or 0)
        end = start + limit
        next_cursor = str(end) if end < len(models) else None
        models = models[start:end]
        return JSONResponse(jsonable_encoder(ModelCatalog(models=models, next_cursor=next_cursor)))
    return JSONResponse(jsonable_encoder(ModelCatalog(models=models)))


@api_router.get("/v1/models/search", dependencies=[Depends(require_api_key)])
async def search_models(
    query: str,
    source: str = "huggingface",
    modality: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> JSONResponse:
    if source != "huggingface":
        raise HTTPException(status_code=400, detail="Unsupported source")

    offset = int(cursor or 0)
    params = {
        "search": query,
        "limit": limit,
        "offset": offset,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get("https://huggingface.co/api/models", params=params)
        response.raise_for_status()
        data = response.json()

    results = []
    for item in data:
        pipeline_tag = item.get("pipeline_tag")
        modality_hint = None
        if pipeline_tag in {"text-generation", "text2text-generation"}:
            modality_hint = "text"
        elif pipeline_tag in {"text-to-image", "image-to-image"}:
            modality_hint = "image"
        elif pipeline_tag in {"text-to-3d", "image-to-3d"}:
            modality_hint = "3d"

        if modality and modality_hint and modality_hint != modality:
            continue

        results.append(
            ModelSearchResult(
                id=item.get("modelId") or item.get("id"),
                name=item.get("modelId") or item.get("id"),
                tags=item.get("tags") or [],
                modality_hints=[modality_hint] if modality_hint else [],
                downloads=item.get("downloads"),
                last_modified=item.get("lastModified"),
            ),
        )

    next_cursor = None
    if len(data) == limit:
        next_cursor = str(offset + limit)

    return JSONResponse(
        jsonable_encoder(ModelSearchResponse(results=results, next_cursor=next_cursor)),
    )


@api_router.get("/v1/providers", dependencies=[Depends(require_api_key)])
async def list_providers() -> JSONResponse:
    settings = get_settings()
    providers = [
        ProviderStatus(name="openai", configured=bool(settings.openai_api_key), supported_modalities=["text"]),
        ProviderStatus(name="anthropic", configured=bool(settings.anthropic_api_key), supported_modalities=["text"]),
        ProviderStatus(name="google", configured=bool(settings.google_api_key), supported_modalities=["text"]),
        ProviderStatus(name="azure", configured=bool(settings.azure_openai_api_key and settings.azure_openai_endpoint), supported_modalities=["text"]),
        ProviderStatus(name="xai", configured=bool(settings.xai_api_key), supported_modalities=["text"]),
        ProviderStatus(name="local", configured=True, supported_modalities=["text", "image", "3d"]),
    ]
    return JSONResponse(jsonable_encoder(ProvidersResponse(providers=providers)))


@api_router.post("/v1/models/download", dependencies=[Depends(require_api_key)])
async def download_model(payload: ModelDownloadRequest) -> JSONResponse:
    registry = get_registry()
    job_store = get_job_store()
    downloader = DownloadService(registry=registry, jobs=job_store)

    job = downloader.start_download(payload)
    return JSONResponse(jsonable_encoder(job), status_code=202)


@api_router.get("/v1/jobs/{job_id}", dependencies=[Depends(require_api_key)])
async def get_job_status(job_id: str) -> JSONResponse:
    job_store = get_job_store()
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(jsonable_encoder(job))


@api_router.delete("/v1/jobs/{job_id}", dependencies=[Depends(require_api_key)])
async def cancel_job(job_id: str) -> JSONResponse:
    job_store = get_job_store()
    job = job_store.cancel_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(jsonable_encoder(job))


@api_router.get("/v1/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str) -> JSONResponse:
    store = get_artifact_store()
    content = store.get_artifact_content(artifact_id)
    return JSONResponse({"artifact_id": artifact_id, "content_base64": encode_inline(content)})


@api_router.get("/v1/models/{model_id}", dependencies=[Depends(require_api_key)])
async def get_model_info(model_id: str) -> JSONResponse:
    """Get detailed information about a specific model including parameters and capabilities."""
    registry = get_registry()
    model = registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return JSONResponse(jsonable_encoder(model))


@api_router.get("/v1/schema", dependencies=[Depends(require_api_key)])
async def get_api_schema() -> JSONResponse:
    """Return API schema documentation including available parameters and their descriptions."""
    schema = {
        "generate": {
            "description": "Generate text, images, or 3D content from prompts",
            "endpoint": "POST /v1/generate",
            "request": {
                "model": {
                    "type": "string",
                    "required": False,
                    "description": "Model ID to use. If omitted, uses the default model (local-text). "
                                   "Can use provider:model format (e.g., 'openai:gpt-4') or model patterns "
                                   "are auto-detected (e.g., 'gpt-4' → OpenAI, 'claude-3-opus' → Anthropic).",
                    "examples": ["local-text", "gpt-4", "claude-3-opus", "openai:gpt-4-turbo", "tinyllama-1.1b-chat-v1.0.Q4_K_M"],
                },
                "modality": {
                    "type": "string",
                    "required": True,
                    "enum": ["text", "image", "3d"],
                    "description": "Type of content to generate.",
                },
                "input": {
                    "type": "object",
                    "required": True,
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Text prompt for generation. Required for text and image generation.",
                        },
                        "images": {
                            "type": "array",
                            "description": "Base64-encoded images for vision models (optional).",
                        },
                    },
                },
                "parameters": {
                    "type": "object",
                    "required": False,
                    "description": "Generation parameters (all optional).",
                    "properties": {
                        "temperature": {
                            "type": "float",
                            "range": [0.0, 2.0],
                            "default": 0.7,
                            "description": "Controls randomness. Lower = more deterministic, higher = more creative.",
                        },
                        "max_tokens": {
                            "type": "integer",
                            "min": 1,
                            "default": 4096,
                            "description": "Maximum number of tokens to generate.",
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format hint (e.g., 'json', 'markdown'). Not all models support this.",
                        },
                    },
                },
                "stream": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, returns Server-Sent Events stream. Only supported for text modality.",
                },
            },
        },
        "models": {
            "description": "List available models",
            "endpoint": "GET /v1/models",
            "query_params": {
                "modality": {"type": "string", "description": "Filter by modality (text, image, 3d)"},
                "limit": {"type": "integer", "description": "Max results per page"},
                "cursor": {"type": "string", "description": "Pagination cursor"},
            },
        },
        "model_detail": {
            "description": "Get detailed model information",
            "endpoint": "GET /v1/models/{model_id}",
        },
        "providers": {
            "description": "List configured providers and their status",
            "endpoint": "GET /v1/providers",
        },
        "download": {
            "description": "Download a model from HuggingFace or URL",
            "endpoint": "POST /v1/models/download",
            "request": {
                "source": {
                    "type": "string",
                    "required": True,
                    "description": "HuggingFace repo ID (e.g., 'TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF') or direct URL",
                },
                "modality": {
                    "type": "string",
                    "required": True,
                    "enum": ["text", "image", "3d"],
                },
            },
        },
    }
    return JSONResponse(schema)
