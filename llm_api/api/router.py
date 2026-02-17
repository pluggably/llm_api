from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
import httpx
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response, StreamingResponse

from llm_api.api.schemas import (
    GenerateRequest,
    GenerateResponse,
    GenerateOutput,
    ModelCatalog,
    ModelDownloadRequest,
    ModelSearchResponse,
    ModelSearchResult,
    RegenerateRequest,
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
from llm_api.runner.mesh_preview import render_mesh_preview
from llm_api.router.selector import (
    ModelNotFoundError,
    ProviderNotSupportedError,
    ProviderNotConfiguredError,
    select_backend,
)
from llm_api.adapters import ProviderError, map_provider_error
from llm_api.sessions import get_session_store
from llm_api.users import get_user_service
from llm_api.processing.images import preprocess_images


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


def _absolute_artifact_url(base_url: str, relative_url: str) -> str:
    """Convert a relative artifact URL to an absolute URL."""
    base = base_url.rstrip("/")
    if relative_url.startswith("http://") or relative_url.startswith("https://"):
        return relative_url
    return f"{base}{relative_url}"


def _make_output_urls_absolute(output: GenerateOutput, base_url: str) -> GenerateOutput:
    """Rewrite artifact URLs in a GenerateOutput to be absolute."""
    if output.artifacts:
        from llm_api.api.schemas import Artifact
        updated = []
        for a in output.artifacts:
            updated.append(
                Artifact(
                    id=a.id,
                    type=a.type,
                    url=_absolute_artifact_url(base_url, a.url),
                    expires_at=a.expires_at,
                )
            )
        output = output.model_copy(update={"artifacts": updated})
    return output


def _provider_model_catalog() -> dict[str, list[ModelInfo]]:
    return {
        "openai": [
            ModelInfo(
                id="gpt-4o-mini",
                name="GPT-4o mini",
                version="latest",
                modality="text",
                provider="openai",
                status="available",
                is_default=False,
            ),
            ModelInfo(
                id="gpt-4o",
                name="GPT-4o",
                version="latest",
                modality="text",
                provider="openai",
                status="available",
                is_default=False,
            ),
        ],
        "anthropic": [
            ModelInfo(
                id="claude-3-5-sonnet",
                name="Claude 3.5 Sonnet",
                version="latest",
                modality="text",
                provider="anthropic",
                status="available",
                is_default=False,
            ),
            ModelInfo(
                id="claude-3-5-haiku",
                name="Claude 3.5 Haiku",
                version="latest",
                modality="text",
                provider="anthropic",
                status="available",
                is_default=False,
            ),
        ],
        "google": [
            ModelInfo(
                id="gemini-1.5-flash",
                name="Gemini 1.5 Flash",
                version="latest",
                modality="text",
                provider="google",
                status="available",
                is_default=False,
            ),
            ModelInfo(
                id="gemini-1.5-pro",
                name="Gemini 1.5 Pro",
                version="latest",
                modality="text",
                provider="google",
                status="available",
                is_default=False,
            ),
        ],
        "xai": [
            ModelInfo(
                id="grok-2",
                name="Grok 2",
                version="latest",
                modality="text",
                provider="xai",
                status="available",
                is_default=False,
            ),
            ModelInfo(
                id="grok-2-mini",
                name="Grok 2 Mini",
                version="latest",
                modality="text",
                provider="xai",
                status="available",
                is_default=False,
            ),
        ],
    }


@api_router.post("/v1/generate", dependencies=[Depends(require_api_key)], response_model=None)
async def generate(request: GenerateRequest, http_request: Request) -> JSONResponse | StreamingResponse:
    settings = get_settings()
    registry = get_registry()
    session_store = get_session_store()
    user_service = get_user_service()

    user = getattr(http_request.state, "user", None)
    user_id = user.get("user_id") if isinstance(user, dict) else None
    provider_credentials: dict[str, dict[str, str]] = {}
    if user_id:
        for provider in ["openai", "anthropic", "google", "azure", "xai", "huggingface"]:
            creds = user_service.get_provider_credentials(user_id, provider)
            if creds:
                provider_credentials[provider] = creds

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
        selection = select_backend(
            model_id,
            registry,
            settings,
            modality=request.modality,
            provider_credentials=provider_credentials,
        )
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
    # Use the model's modality - clients don't need to specify it
    effective_modality = selection.model.modality

    # Image preprocessing — resize/re-encode per model constraints
    preprocessing_warnings: list[str] = []
    if request.input.images:
        caps = selection.model.capabilities
        pp_result = preprocess_images(
            request.input.images,
            model_max_edge=caps.image_input_max_edge if caps else None,
            model_max_pixels=caps.image_input_max_pixels if caps else None,
            model_formats=caps.image_input_formats if caps else None,
            provider=selection.model.provider,
        )
        request = request.model_copy(
            update={"input": request.input.model_copy(update={"images": pp_result.images})}
        )
        preprocessing_warnings = pp_result.warnings

    base_url = str(http_request.base_url)

    # Handle streaming requests
    if request.stream:
        if effective_modality == "text":
            # Stream text responses token by token (or in chunks)
            async def event_stream() -> AsyncGenerator[str, None]:
                try:
                    # Run blocking generation in thread pool to not block event loop
                    output_text = await asyncio.to_thread(
                        selection.adapter.generate_text, request.input.prompt or ""
                    )
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
                    effective_modality,
                    request.input.model_dump(mode="json"),
                    {"stream": True},
                    effective_state_tokens,
                )
            return StreamingResponse(event_stream(), media_type="text/event-stream")
        else:
            # For non-text modalities, generate and wrap result in SSE format
            # so frontend streaming parser can handle it uniformly
            async def single_event_stream() -> AsyncGenerator[str, None]:
                request_id = str(uuid.uuid4())
                
                # Send initial heartbeat to indicate processing started
                yield ": heartbeat\n\n"
                
                # Run generation in background and send keepalive heartbeats
                import concurrent.futures
                loop = asyncio.get_event_loop()
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                
                try:
                    if effective_modality == "image":
                        future = loop.run_in_executor(
                            executor,
                            selection.adapter.generate_image,
                            request.input.prompt or ""
                        )
                    else:  # 3d
                        future = loop.run_in_executor(
                            executor,
                            selection.adapter.generate_3d,
                            request.input.prompt or ""
                        )
                    
                    # Wait for result while sending keepalive heartbeats every 15 seconds
                    while True:
                        try:
                            content = await asyncio.wait_for(
                                asyncio.shield(future), 
                                timeout=15.0
                            )
                            break  # Got result
                        except asyncio.TimeoutError:
                            # Send keepalive heartbeat (SSE comment)
                            yield ": heartbeat\n\n"
                            continue
                    
                    # Build response based on modality
                    if effective_modality == "image":
                        artifacts = []
                        if len(content) > _artifact_inline_threshold_bytes():
                            artifact = get_artifact_store().create_artifact(content, "image")
                            artifacts.append(artifact)
                            output = GenerateOutput(artifacts=artifacts)
                        else:
                            output = GenerateOutput(images=[encode_inline(content)])
                    else:  # 3d
                        artifacts = []
                        preview_bytes = render_mesh_preview(content)
                        if preview_bytes:
                            artifacts.append(
                                get_artifact_store().create_artifact(
                                    preview_bytes, "image"
                                )
                            )
                        if len(content) > _artifact_inline_threshold_bytes():
                            artifact = get_artifact_store().create_artifact(content, "mesh")
                            artifacts.append(artifact)
                            output = GenerateOutput(artifacts=artifacts)
                        else:
                            output = GenerateOutput(
                                mesh=encode_inline(content),
                                artifacts=artifacts or None,
                            )
                    
                    # Rewrite artifact URLs to absolute
                    output = _make_output_urls_absolute(output, base_url)

                    response = GenerateResponse(
                        request_id=request_id,
                        model=model_id,
                        modality=effective_modality,
                        session_id=session_id,
                        state_tokens=effective_state_tokens,
                        output=output,
                        usage=Usage(),
                        warnings=preprocessing_warnings or None,
                    )
                    payload = json.dumps(jsonable_encoder(response))
                    import logging
                    logging.info(f"Sending SSE response: modality={effective_modality}, payload_len={len(payload)}")
                    yield f"data: {payload}\n\n"
                    yield "data: [DONE]\n\n"
                    logging.info("SSE response sent with [DONE]")
                except ProviderError as exc:
                    error = map_provider_error(exc)
                    payload = json.dumps({"error": {"code": error.code, "message": error.message}})
                    yield f"data: {payload}\n\n"
                except Exception as exc:
                    payload = json.dumps({"error": {"code": "internal_error", "message": str(exc)}})
                    yield f"data: {payload}\n\n"
                finally:
                    executor.shutdown(wait=False)

            if session:
                session_store.append_message(
                    session_id,
                    effective_modality,
                    request.input.model_dump(mode="json"),
                    {"stream": True},
                    effective_state_tokens,
                )
            return StreamingResponse(single_event_stream(), media_type="text/event-stream")

    request_id = str(uuid.uuid4())

    # Non-streaming path - also use thread pool for blocking operations
    try:
        if effective_modality == "text":
            output_text = await asyncio.to_thread(
                selection.adapter.generate_text, request.input.prompt or ""
            )
            output = GenerateOutput(text=output_text)
            usage = _build_usage(request.input.prompt, output_text)
        elif effective_modality == "image":
            content = await asyncio.to_thread(
                selection.adapter.generate_image, request.input.prompt or ""
            )
            artifacts = []
            if len(content) > _artifact_inline_threshold_bytes():
                artifact = get_artifact_store().create_artifact(content, "image")
                artifacts.append(artifact)
                output = GenerateOutput(artifacts=artifacts)
            else:
                output = GenerateOutput(images=[encode_inline(content)])
            usage = Usage()
        else:
            content = await asyncio.to_thread(
                selection.adapter.generate_3d, request.input.prompt or ""
            )
            artifacts = []
            preview_bytes = render_mesh_preview(content)
            if preview_bytes:
                artifacts.append(
                    get_artifact_store().create_artifact(preview_bytes, "image")
                )
            if len(content) > _artifact_inline_threshold_bytes():
                artifact = get_artifact_store().create_artifact(content, "mesh")
                artifacts.append(artifact)
                output = GenerateOutput(artifacts=artifacts)
            else:
                output = GenerateOutput(
                    mesh=encode_inline(content),
                    artifacts=artifacts or None,
                )
            usage = Usage()
    except ProviderError as exc:
        error = map_provider_error(exc)
        raise HTTPException(
            status_code=error.status_code,
            detail={"code": error.code, "message": error.message},
        ) from exc

    # Rewrite artifact URLs to absolute
    output = _make_output_urls_absolute(output, base_url)

    response = GenerateResponse(
        request_id=request_id,
        model=model_id,
        modality=effective_modality,
        session_id=session_id,
        state_tokens=effective_state_tokens,
        output=output,
        usage=usage,
        warnings=preprocessing_warnings or None,
    )
    if session:
        session_store.append_message(
            session_id,
            effective_modality,
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
async def generate_with_session(session_id: str, request: GenerateRequest, http_request: Request) -> JSONResponse | StreamingResponse:
    session_request = request.model_copy(update={"session_id": session_id})
    return await generate(session_request, http_request)


@api_router.post("/v1/sessions/{session_id}/regenerate", dependencies=[Depends(require_api_key)], response_model=None)
async def regenerate(session_id: str, request: RegenerateRequest, http_request: Request) -> JSONResponse | StreamingResponse:
    """Re-generate the last assistant response in a session.

    Finds the last user turn, removes the last assistant message, and
    replays through the generate pipeline with the same (or overridden) model/parameters.
    """
    session_store = get_session_store()
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is closed")
    if not session.messages:
        raise HTTPException(status_code=400, detail="Session has no messages to regenerate")

    # Find last user turn
    last_user_msg = None
    for msg in reversed(session.messages):
        user_prompt = msg.input.get("prompt") if msg.input else None
        if user_prompt:
            last_user_msg = msg
            break

    if not last_user_msg:
        raise HTTPException(status_code=400, detail="No user message found in session")

    # Remove last message (the assistant response being regenerated)
    from sqlalchemy import delete as sa_delete
    from llm_api.db.database import get_db_session as get_db
    from llm_api.db.models import SessionMessageRecord as DbMsgRecord

    with get_db() as db:
        # Delete the last message by highest sequence number
        from sqlalchemy import select as sa_select, func as sa_func
        max_seq = db.execute(
            sa_select(sa_func.max(DbMsgRecord.sequence)).where(
                DbMsgRecord.session_id == session_id,
            )
        ).scalar()
        if max_seq is not None:
            db.execute(
                sa_delete(DbMsgRecord).where(
                    DbMsgRecord.session_id == session_id,
                    DbMsgRecord.sequence == max_seq,
                )
            )

    # Build a generate request from the original user input
    prompt = last_user_msg.input.get("prompt", "")
    images = last_user_msg.input.get("images")
    modality = last_user_msg.modality

    gen_request = GenerateRequest(
        model=request.model,
        session_id=session_id,
        modality=modality,
        input={"prompt": prompt, "images": images},
        parameters=request.parameters,
        stream=request.stream,
    )
    return await generate(gen_request, http_request)


@api_router.get("/v1/models", dependencies=[Depends(require_api_key)])
async def list_models(
    http_request: Request,
    modality: str | None = None,
    limit: int | None = None,
    cursor: str | None = None,
) -> JSONResponse:
    registry = get_registry()
    user_service = get_user_service()

    models = registry.list_models(modality=modality)
    models_by_id = {model.id: model for model in models}

    user = getattr(http_request.state, "user", None)
    user_id = user.get("user_id") if isinstance(user, dict) else None
    if user_id:
        catalog = _provider_model_catalog()
        for provider, provider_models in catalog.items():
            creds = user_service.get_provider_credentials(user_id, provider)
            if not creds:
                continue
            for model in provider_models:
                if modality and model.modality != modality:
                    continue
                models_by_id.setdefault(model.id, model)

    models = list(models_by_id.values())
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
async def list_providers(http_request: Request) -> JSONResponse:
    user_service = get_user_service()
    user = getattr(http_request.state, "user", None)
    user_id = user.get("user_id") if isinstance(user, dict) else None

    def _has_creds(provider: str) -> bool:
        if not user_id:
            return False
        return user_service.get_provider_credentials(user_id, provider) is not None

    providers = [
        ProviderStatus(name="openai", configured=_has_creds("openai"), supported_modalities=["text"]),
        ProviderStatus(name="anthropic", configured=_has_creds("anthropic"), supported_modalities=["text"]),
        ProviderStatus(name="google", configured=_has_creds("google"), supported_modalities=["text"]),
        ProviderStatus(name="azure", configured=_has_creds("azure"), supported_modalities=["text"]),
        ProviderStatus(name="xai", configured=_has_creds("xai"), supported_modalities=["text"]),
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


@api_router.get("/v1/jobs", dependencies=[Depends(require_api_key)])
async def list_jobs() -> JSONResponse:
    job_store = get_job_store()
    jobs = list(job_store.jobs.values())
    # Sort by created_at descending
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return JSONResponse(jsonable_encoder({"jobs": jobs}))


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
async def get_artifact(artifact_id: str) -> Response:
    """Return artifact content as raw bytes with appropriate content-type."""
    store = get_artifact_store()
    content = store.get_artifact_content(artifact_id)
    # Detect content type from magic bytes
    content_type = "application/octet-stream"
    if content[:8] == b'\x89PNG\r\n\x1a\n':
        content_type = "image/png"
    elif content[:2] == b'\xff\xd8':
        content_type = "image/jpeg"
    elif content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        content_type = "image/webp"
    elif content[:6] in (b'GIF87a', b'GIF89a'):
        content_type = "image/gif"
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@api_router.get("/v1/models/{model_id:path}", dependencies=[Depends(require_api_key)])
async def get_model_info(model_id: str) -> JSONResponse:
    """Get detailed information about a specific model including parameters and capabilities."""
    registry = get_registry()
    model = registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return JSONResponse(jsonable_encoder(model))


# Model-specific parameter schemas by modality
_TEXT_MODEL_PARAMETERS = {
    "temperature": {
        "type": "number",
        "title": "Temperature",
        "description": "Controls randomness. Lower = more deterministic, higher = more creative.",
        "default": 0.7,
        "minimum": 0.0,
        "maximum": 2.0,
    },
    "max_tokens": {
        "type": "integer",
        "title": "Max Tokens",
        "description": "Maximum number of tokens to generate.",
        "default": 4096,
        "minimum": 1,
        "maximum": 128000,
    },
    "top_p": {
        "type": "number",
        "title": "Top P",
        "description": "Nucleus sampling probability threshold.",
        "default": 1.0,
        "minimum": 0.0,
        "maximum": 1.0,
    },
    "format": {
        "type": "string",
        "title": "Output Format",
        "description": "Optional format hint (e.g., 'json', 'markdown').",
        "enum": ["text", "json", "markdown"],
    },
}

_IMAGE_MODEL_PARAMETERS = {
    "width": {
        "type": "integer",
        "title": "Width",
        "description": "Image width in pixels. Use 512 for faster CPU inference.",
        "default": 512,
        "minimum": 256,
        "maximum": 4096,
    },
    "height": {
        "type": "integer",
        "title": "Height",
        "description": "Image height in pixels. Use 512 for faster CPU inference.",
        "default": 512,
        "minimum": 256,
        "maximum": 4096,
    },
    "num_inference_steps": {
        "type": "integer",
        "title": "Inference Steps",
        "description": "Number of denoising steps. Turbo models need 1-4, standard models need 20-50.",
        "default": 4,
        "minimum": 1,
        "maximum": 150,
    },
    "guidance_scale": {
        "type": "number",
        "title": "Guidance Scale",
        "description": "How closely to follow the prompt. Use 0 for turbo models, 7.5 for standard.",
        "default": 0.0,
        "minimum": 0.0,
        "maximum": 20.0,
    },
    "negative_prompt": {
        "type": "string",
        "title": "Negative Prompt",
        "description": "What to avoid in the image.",
    },
    "seed": {
        "type": "integer",
        "title": "Seed",
        "description": "Random seed for reproducibility. Use -1 for random.",
        "default": -1,
        "minimum": -1,
    },
    "scheduler": {
        "type": "string",
        "title": "Scheduler",
        "description": "Sampling scheduler algorithm.",
        "default": "euler",
        "enum": ["euler", "euler_a", "ddim", "dpm", "dpm++", "lms", "pndm", "heun", "unipc"],
    },
    "clip_skip": {
        "type": "integer",
        "title": "CLIP Skip",
        "description": "Number of CLIP layers to skip. Higher values = more stylized.",
        "default": 0,
        "minimum": 0,
        "maximum": 12,
    },
    "num_images": {
        "type": "integer",
        "title": "Number of Images",
        "description": "Number of images to generate per prompt.",
        "default": 1,
        "minimum": 1,
        "maximum": 4,
    },
    "strength": {
        "type": "number",
        "title": "Strength",
        "description": "Denoising strength for img2img. 1.0 = full denoise, 0.0 = no change.",
        "default": 0.8,
        "minimum": 0.0,
        "maximum": 1.0,
    },
    "eta": {
        "type": "number",
        "title": "Eta (DDIM)",
        "description": "Eta parameter for DDIM scheduler. 0 = deterministic.",
        "default": 0.0,
        "minimum": 0.0,
        "maximum": 1.0,
    },
}

_3D_MODEL_PARAMETERS = {
    "num_inference_steps": {
        "type": "integer",
        "title": "Inference Steps",
        "description": "Number of generation steps.",
        "default": 64,
        "minimum": 1,
        "maximum": 256,
    },
    "guidance_scale": {
        "type": "number",
        "title": "Guidance Scale",
        "description": "How closely to follow the prompt.",
        "default": 15.0,
        "minimum": 1.0,
        "maximum": 100.0,
    },
}


@api_router.get("/v1/schema", dependencies=[Depends(require_api_key)])
async def get_api_schema(model: str | None = None) -> JSONResponse:
    """Return model-specific parameter schema or general API documentation.
    
    If model query param is provided, returns parameter schema for that model.
    Otherwise returns general API documentation.
    """
    # If a model is specified, return model-specific parameter schema
    if model:
        registry = get_registry()
        model_info = registry.get_model(model)
        
        # Determine modality and select appropriate parameters
        modality = model_info.modality if model_info else "text"
        
        if modality == "image":
            properties = _IMAGE_MODEL_PARAMETERS
        elif modality == "3d":
            properties = _3D_MODEL_PARAMETERS
        else:
            properties = _TEXT_MODEL_PARAMETERS
        
        return JSONResponse({
            "model_id": model,
            "version": model_info.version if model_info else None,
            "properties": properties,
        })
    
    # Otherwise return general API documentation
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
