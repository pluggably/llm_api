from __future__ import annotations

import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse

from llm_api.api.schemas import (
    GenerateRequest,
    GenerateResponse,
    GenerateOutput,
    ModelCatalog,
    ModelDownloadRequest,
    Usage,
    ModelInfo,
    ProvidersResponse,
    ProviderStatus,
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

    model_id = request.model

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
            text = f"Stub response for: {request.input.prompt or ''}"
            if request.input.prompt == "RAISE_ERROR":
                yield "data: {\"error\": \"stream_error\"}\n\n"
                return
            for token in text.split():
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"

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
        output=output,
        usage=usage,
    )
    return JSONResponse(jsonable_encoder(response))


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
