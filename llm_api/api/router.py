from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import uuid
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)
TEXT_GENERATION_TIMEOUT_SECONDS = 180.0

from fastapi import APIRouter, Depends, HTTPException, Request
import httpx
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response, StreamingResponse

from llm_api.api.schemas import (
    AvailabilityInfo,
    CreditsStatus,
    GenerateInput,
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
    BackendSelection,
    ModelNotFoundError,
    ProviderNotSupportedError,
    ProviderNotConfiguredError,
    select_backend,
    select_provider_tier_fallback,
)
from llm_api.api.schemas import SelectionInfo as _SelectionInfo
from llm_api.adapters import ProviderError, map_provider_error
from llm_api.sessions import get_session_store
from llm_api.users import get_user_service
from llm_api.processing.images import preprocess_images
from llm_api.integrations.provider_discovery import (
    get_provider_availability,
    get_provider_catalog_models,
    get_cached_availability,
    mark_provider_quota_exhausted,
    mark_provider_rate_limited,
)


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
        for provider in ["openai", "anthropic", "google", "azure", "xai", "deepseek", "huggingface"]:
            creds = user_service.get_provider_credentials(user_id, provider)
            if creds:
                provider_credentials[provider] = creds

    logger.debug(
        "generate: user_id=%s model=%r session_id=%r providers_with_creds=%s",
        user_id, request.model, request.session_id,
        list(provider_credentials.keys()),
    )

    provider_preference = request.provider
    provider_models = None
    credits_status: CreditsStatus | None = None
    if provider_preference:
        if user_id:
            creds = user_service.get_provider_credentials(user_id, provider_preference)
            if creds:
                availability = get_provider_availability(user_id, provider_preference, creds)
                provider_models = availability.models
                credits_status = availability.credits_status
            else:
                credits_status = CreditsStatus(provider=provider_preference, status="exhausted")
        else:
            credits_status = CreditsStatus(provider=provider_preference, status="unknown")

    selection_mode = request.selection_mode or (
        "model" if request.model and request.model != "auto" else "auto"
    )
    model_id = request.model
    if model_id == "auto":
        model_id = None
    if selection_mode == "model" and not model_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "model_required",
                "message": "Selection mode 'model' requires a specific model ID.",
            },
        )
    if model_id is not None:
        selection_mode = "model"
    session_id = request.session_id
    session = None
    if session_id:
        session = session_store.get_session(session_id)
        if not session:
            logger.warning("generate: session_id=%r not found", session_id)
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        logger.debug("generate: session found session_id=%s status=%s", session_id, session.status)
        if session.status != "active":
            raise HTTPException(status_code=400, detail="Session is closed")

    effective_state_tokens = request.state_tokens
    if session and effective_state_tokens is None:
        effective_state_tokens = session.state_tokens

    try:
        request_parameters = (
            request.parameters.model_dump(exclude_none=True)
            if request.parameters is not None
            else None
        )
        selection = select_backend(
            model_id,
            registry,
            settings,
            modality=request.modality,
            selection_mode=selection_mode,
            prompt=request.input.prompt,
            images=request.input.images,
            mesh=request.input.mesh,
            provider=provider_preference,
            provider_models=provider_models,
            credits_status=credits_status,
            provider_credentials=provider_credentials,
            parameters=request_parameters,
        )
    except ModelNotFoundError as exc:
        logger.warning("generate: ModelNotFoundError model_id=%r error=%s", model_id, exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderNotSupportedError as exc:
        logger.warning("generate: ProviderNotSupportedError model_id=%r error=%s", model_id, exc)
        raise HTTPException(
            status_code=400,
            detail={"code": "unsupported_provider", "message": str(exc)},
        ) from exc
    except ProviderNotConfiguredError as exc:
        logger.warning("generate: ProviderNotConfiguredError model_id=%r error=%s", model_id, exc)
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
                    model_payload = json.dumps(
                        {
                            "event": "model_selected",
                            "model": model_id,
                            "model_name": selection.model.name,
                            "modality": effective_modality,
                            "provider": selection.model.provider,
                            "fallback_used": selection.selection.fallback_used if selection.selection else False,
                            "fallback_reason": selection.selection.fallback_reason if selection.selection else None,
                        }
                    )
                    yield f"data: {model_payload}\n\n"
                    # Run blocking generation with periodic keepalive heartbeats
                    # (local HF models can take 30-120s; without heartbeats the
                    # connection may time out or the client may stall forever)
                    _loop = asyncio.get_running_loop()
                    _gen_future = _loop.run_in_executor(
                        None, selection.adapter.generate_text, request.input.prompt or ""
                    )
                    _deadline = _loop.time() + TEXT_GENERATION_TIMEOUT_SECONDS
                    while True:
                        try:
                            output_text = await asyncio.wait_for(
                                asyncio.shield(_gen_future), timeout=15.0
                            )
                            break
                        except asyncio.TimeoutError:
                            if _loop.time() >= _deadline:
                                err_payload = json.dumps(
                                    {
                                        "error": {
                                            "code": "generation_timeout",
                                            "message": (
                                                "Local generation exceeded "
                                                f"{int(TEXT_GENERATION_TIMEOUT_SECONDS)}s. "
                                                "Try a smaller max_tokens value or a smaller model."
                                            ),
                                        }
                                    }
                                )
                                yield f"data: {err_payload}\n\n"
                                yield "data: [DONE]\n\n"
                                return
                            yield ": heartbeat\n\n"
                except ProviderError as exc:
                    # Tiered fallback on rate-limit / provider overload:
                    #   1) Same provider's cheaper tier model (skips if quota exhausted)
                    #   2) Local free model
                    if exc.status_code in (429, 503):
                        failed_provider = selection.model.provider or ""
                        base_reason = "rate_limited" if exc.status_code == 429 else "provider_overloaded"
                        is_quota_exceeded = exc.error_code == "insufficient_quota"
                        logger.warning(
                            "generate: provider %s returned %d (error_code=%s), starting fallback chain",
                            failed_provider, exc.status_code, exc.error_code,
                        )

                        # Write back rate-limit / quota status to the availability cache
                        if user_id:
                            if is_quota_exceeded:
                                mark_provider_quota_exhausted(user_id, failed_provider)
                            elif exc.status_code == 429:
                                mark_provider_rate_limited(user_id, failed_provider)

                        # Also check cache: a previous request may have already marked exhausted
                        if not is_quota_exceeded and user_id:
                            cached = get_cached_availability(user_id, failed_provider)
                            if cached and cached.credits_status.status == "exhausted":
                                is_quota_exceeded = True
                                logger.info(
                                    "generate: provider %s already exhausted in cache, skipping tier fallback",
                                    failed_provider,
                                )

                        fb: Optional[BackendSelection] = None
                        fallback_output: Optional[str] = None

                        # Step 1: cheaper tier from same provider (skip if quota exhausted)
                        if not is_quota_exceeded:
                            try:
                                fb = select_provider_tier_fallback(
                                    failed_provider,
                                    selection.model.id,
                                    settings,
                                    provider_credentials=provider_credentials,
                                    modality=effective_modality,
                                    parameters=request_parameters,
                                )
                                fallback_output = await asyncio.wait_for(
                                    asyncio.to_thread(
                                        fb.adapter.generate_text,
                                        request.input.prompt or "",
                                    ),
                                    timeout=TEXT_GENERATION_TIMEOUT_SECONDS,
                                )
                                logger.info(
                                    "generate: tier fallback to %s succeeded for provider %s",
                                    fb.model.id, failed_provider,
                                )
                            except Exception as tier_exc:
                                logger.warning(
                                    "generate: tier fallback for %s failed: %s",
                                    failed_provider, tier_exc,
                                )
                                fb = None

                        # Step 2: local free model
                        if fb is None:
                            local_reason = "quota_exceeded" if is_quota_exceeded else f"{base_reason}_local"
                            try:
                                local_fb = select_backend(
                                    None, registry, settings,
                                    modality=effective_modality,
                                    selection_mode="free_only",
                                    provider_credentials=provider_credentials,
                                    parameters=request_parameters,
                                )
                                fallback_output = await asyncio.wait_for(
                                    asyncio.to_thread(
                                        local_fb.adapter.generate_text,
                                        request.input.prompt or "",
                                    ),
                                    timeout=TEXT_GENERATION_TIMEOUT_SECONDS,
                                )
                                if local_fb.selection:
                                    local_fb.selection.fallback_used = True
                                    local_fb.selection.fallback_reason = local_reason
                                else:
                                    local_fb.selection = _SelectionInfo(
                                        selected_model=local_fb.model.id,
                                        selected_provider=local_fb.model.provider,
                                        fallback_used=True,
                                        fallback_reason=local_reason,
                                    )
                                fb = local_fb
                                logger.info(
                                    "generate: local fallback to %s succeeded after %d from %s",
                                    local_fb.model.id, exc.status_code, failed_provider,
                                )
                            except Exception as fb_exc:
                                logger.warning("generate: local fallback also failed: %s", fb_exc)

                        if fb is not None and fallback_output is not None:
                            fb_reason = fb.selection.fallback_reason if fb.selection else base_reason
                            fb_payload = json.dumps({
                                "event": "model_selected",
                                "model": fb.model.id,
                                "model_name": fb.model.name,
                                "modality": effective_modality,
                                "provider": fb.model.provider,
                                "fallback_used": True,
                                "fallback_reason": fb_reason,
                            })
                            yield f"data: {fb_payload}\n\n"
                            payload = json.dumps({"choices": [{"delta": {"content": fallback_output}}]})
                            yield f"data: {payload}\n\n"
                            yield "data: [DONE]\n\n"
                            return
                    error = map_provider_error(exc)
                    payload = json.dumps({"error": {"code": error.code, "message": error.message}})
                    yield f"data: {payload}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                except Exception as exc:
                    logger.exception("generate: unexpected error during local text generation")
                    err_payload = json.dumps({"error": {"code": "internal_error", "message": str(exc)}})
                    yield f"data: {err_payload}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                payload = json.dumps({"choices": [{"delta": {"content": output_text}}]})
                yield f"data: {payload}\n\n"
                yield "data: [DONE]\n\n"

            if session:
                assert session_id is not None
                session_store.append_message(
                    session_id,
                    effective_modality,
                    request.input.model_dump(mode="json"),
                    {"stream": True},
                    effective_state_tokens,
                )
            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        else:
            # For non-text modalities, generate and wrap result in SSE format
            # so frontend streaming parser can handle it uniformly
            async def single_event_stream() -> AsyncGenerator[str, None]:
                request_id = str(uuid.uuid4())
                
                # Send initial heartbeat to indicate processing started
                yield ": heartbeat\n\n"

                model_payload = json.dumps(
                    {
                        "event": "model_selected",
                        "model": model_id,
                        "model_name": selection.model.name,
                        "modality": effective_modality,
                        "provider": selection.model.provider,
                        "fallback_used": selection.selection.fallback_used if selection.selection else False,
                        "fallback_reason": selection.selection.fallback_reason if selection.selection else None,
                    }
                )
                yield f"data: {model_payload}\n\n"
                
                # Run generation in background and send keepalive heartbeats
                loop = asyncio.get_running_loop()
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
                        selection=selection.selection,
                        credits_status=selection.credits_status,
                        output=output,
                        usage=Usage(),
                        warnings=preprocessing_warnings or None,
                    )
                    payload = json.dumps(jsonable_encoder(response))
                    logger.info("Sending SSE response: modality=%s, payload_len=%d", effective_modality, len(payload))
                    yield f"data: {payload}\n\n"
                    yield "data: [DONE]\n\n"
                    logger.info("SSE response sent with [DONE]")
                except ProviderError as exc:
                    error = map_provider_error(exc)
                    payload = json.dumps({"error": {"code": error.code, "message": error.message}})
                    yield f"data: {payload}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as exc:
                    payload = json.dumps({"error": {"code": "internal_error", "message": str(exc)}})
                    yield f"data: {payload}\n\n"
                    yield "data: [DONE]\n\n"
                finally:
                    executor.shutdown(wait=False)

            if session:
                assert session_id is not None
                session_store.append_message(
                    session_id,
                    effective_modality,
                    request.input.model_dump(mode="json"),
                    {"stream": True},
                    effective_state_tokens,
                )
            return StreamingResponse(
                single_event_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

    request_id = str(uuid.uuid4())

    # Non-streaming path - also use thread pool for blocking operations
    try:
        if effective_modality == "text":
            try:
                output_text = await asyncio.wait_for(
                    asyncio.to_thread(
                        selection.adapter.generate_text,
                        request.input.prompt or "",
                    ),
                    timeout=TEXT_GENERATION_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError as exc:
                raise ProviderError(
                    504,
                    (
                        "Text generation timed out after "
                        f"{int(TEXT_GENERATION_TIMEOUT_SECONDS)}s. "
                        "Try a smaller max_tokens value or a smaller model."
                    ),
                ) from exc
            except ProviderError as exc:
                if exc.status_code in (429, 503):
                    failed_provider = selection.model.provider or ""
                    base_reason = "rate_limited" if exc.status_code == 429 else "provider_overloaded"
                    is_quota_exceeded = exc.error_code == "insufficient_quota"
                    logger.warning(
                        "generate: provider %s returned %d (error_code=%s), starting fallback chain",
                        failed_provider, exc.status_code, exc.error_code,
                    )

                    # Write back rate-limit / quota status to the availability cache
                    if user_id:
                        if is_quota_exceeded:
                            mark_provider_quota_exhausted(user_id, failed_provider)
                        elif exc.status_code == 429:
                            mark_provider_rate_limited(user_id, failed_provider)

                    # Also check cache: a previous request may have already marked exhausted
                    if not is_quota_exceeded and user_id:
                        cached_ns = get_cached_availability(user_id, failed_provider)
                        if cached_ns and cached_ns.credits_status.status == "exhausted":
                            is_quota_exceeded = True
                            logger.info(
                                "generate: provider %s already exhausted in cache, skipping tier fallback",
                                failed_provider,
                            )

                    fb_ns: Optional[BackendSelection] = None

                    # Step 1: cheaper tier from same provider (skip if quota exhausted)
                    if not is_quota_exceeded:
                        try:
                            tier_fb = select_provider_tier_fallback(
                                failed_provider,
                                selection.model.id,
                                settings,
                                provider_credentials=provider_credentials,
                                modality=effective_modality,
                                parameters=request_parameters,
                            )
                            output_text = await asyncio.wait_for(
                                asyncio.to_thread(
                                    tier_fb.adapter.generate_text,
                                    request.input.prompt or "",
                                ),
                                timeout=TEXT_GENERATION_TIMEOUT_SECONDS,
                            )
                            fb_ns = tier_fb
                            logger.info(
                                "generate: tier fallback to %s succeeded for provider %s",
                                tier_fb.model.id, failed_provider,
                            )
                        except Exception as tier_exc:
                            logger.warning(
                                "generate: tier fallback for %s failed: %s",
                                failed_provider, tier_exc,
                            )

                    # Step 2: local free model
                    if fb_ns is None:
                        local_reason = "quota_exceeded" if is_quota_exceeded else f"{base_reason}_local"
                        try:
                            local_fb = select_backend(
                                None, registry, settings,
                                modality=effective_modality,
                                selection_mode="free_only",
                                provider_credentials=provider_credentials,
                                parameters=request_parameters,
                            )
                            output_text = await asyncio.wait_for(
                                asyncio.to_thread(
                                    local_fb.adapter.generate_text,
                                    request.input.prompt or "",
                                ),
                                timeout=TEXT_GENERATION_TIMEOUT_SECONDS,
                            )
                            if local_fb.selection:
                                local_fb.selection.fallback_used = True
                                local_fb.selection.fallback_reason = local_reason
                            else:
                                local_fb.selection = _SelectionInfo(
                                    selected_model=local_fb.model.id,
                                    selected_provider=local_fb.model.provider,
                                    fallback_used=True,
                                    fallback_reason=local_reason,
                                )
                            fb_ns = local_fb
                            logger.info(
                                "generate: local fallback to %s succeeded after %d from %s",
                                local_fb.model.id, exc.status_code, failed_provider,
                            )
                        except Exception as fb_exc:
                            logger.warning("generate: local fallback also failed: %s", fb_exc)
                            raise exc  # re-raise original error

                    if fb_ns is not None:
                        selection = fb_ns
                        model_id = fb_ns.model.id
                    else:
                        raise exc
                else:
                    raise
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
        selection=selection.selection,
        credits_status=selection.credits_status,
        output=output,
        usage=usage,
        warnings=preprocessing_warnings or None,
    )
    if session:
        assert session_id is not None
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
    mesh = last_user_msg.input.get("mesh")
    modality = last_user_msg.modality
    if modality not in ("text", "image", "3d"):
        raise HTTPException(status_code=400, detail="Unsupported modality in session history")

    gen_request = GenerateRequest(
        model=request.model,
        session_id=session_id,
        modality=modality,
        input=GenerateInput(prompt=prompt, images=images, mesh=mesh),
        parameters=request.parameters,
        stream=request.stream,
        selection_mode=request.selection_mode,
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
    for provider in ["openai", "anthropic", "google", "azure", "xai", "deepseek"]:
        creds = user_service.get_provider_credentials(user_id, provider) if user_id else None
        if creds:
            availability = get_provider_availability(user_id, provider, creds)
            provider_models = availability.models
            credits_status: CreditsStatus | None = availability.credits_status
            access = "available"
        else:
            provider_models = get_provider_catalog_models(provider)
            credits_status = None
            access = "locked"
        for model in provider_models:
            if modality and model.modality != modality:
                continue
            model.availability = AvailabilityInfo(
                provider=provider,
                access=access,
                credits_status=credits_status,
            )
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
        ProviderStatus(name="huggingface", configured=_has_creds("huggingface"), supported_modalities=["text", "image"]),
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


@api_router.post("/v1/models/{model_id:path}/default", dependencies=[Depends(require_api_key)])
async def set_default_model(model_id: str) -> JSONResponse:
    """Set the default model for the model's modality (one default per modality)."""
    registry = get_registry()
    model = registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    registry.set_default_model(model.modality, model.id)
    updated = registry.get_model(model.id)
    return JSONResponse(jsonable_encoder(updated or model))


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
