"""Model lifecycle and runtime API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from llm_api.api.schemas import (
    CancelRequestResponse,
    LoadedModelInfo,
    LoadedModelsResponse,
    LoadModelRequest,
    ModelRuntimeStatus,
    QueuePositionResponse,
)
from llm_api.auth import require_api_key
from llm_api.lifecycle import get_lifecycle_manager
from llm_api.queue import get_queue_manager
from llm_api.registry import get_registry


lifecycle_router = APIRouter(tags=["lifecycle"])


@lifecycle_router.get("/v1/models/{model_id:path}/status", dependencies=[Depends(require_api_key)])
async def get_model_runtime_status(model_id: str) -> JSONResponse:
    """Get the runtime status of a model (unloaded, loading, loaded, busy)."""
    registry = get_registry()
    lifecycle = get_lifecycle_manager()
    queue = get_queue_manager()
    
    # Check model exists
    model = registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    
    runtime_status = lifecycle.get_status(model_id)
    queue_info = queue.get_queue_info(model_id)
    
    response = ModelRuntimeStatus(
        model_id=model_id,
        runtime_status=runtime_status,
        queue_depth=queue_info["queue_depth"],
    )
    
    return JSONResponse(jsonable_encoder(response))


@lifecycle_router.post("/v1/models/{model_id:path}/load", dependencies=[Depends(require_api_key)])
async def load_model(model_id: str, request: LoadModelRequest | None = None) -> JSONResponse:
    """Pre-load a model into memory."""
    if request is None:
        request = LoadModelRequest()
    
    registry = get_registry()
    lifecycle = get_lifecycle_manager()
    
    # Check model exists
    model = registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    
    # Check if already loaded or loading
    status = lifecycle.get_status(model_id)
    if status == "loaded" or status == "busy":
        return JSONResponse({
            "model_id": model_id,
            "status": status,
            "message": "Model already loaded",
        })
    
    if status == "loading":
        if request.wait:
            await lifecycle.load_model(
                model_id,
                wait=True,
                use_fallback=request.use_fallback,
                fallback_model_id=request.fallback_model_id,
            )
            return JSONResponse({
                "model_id": model_id,
                "status": "loaded",
                "message": "Model loaded",
            })
        else:
            return JSONResponse({
                "model_id": model_id,
                "status": "loading",
                "message": "Model is loading",
            }, status_code=202)
    
    # Start loading
    if request.wait:
        await lifecycle.load_model(
            model_id,
            wait=True,
            use_fallback=request.use_fallback,
            fallback_model_id=request.fallback_model_id,
        )
        return JSONResponse({
            "model_id": model_id,
            "status": "loaded",
            "message": "Model loaded",
        })
    else:
        # Start async load
        import asyncio
        asyncio.create_task(lifecycle.load_model(model_id))
        return JSONResponse({
            "model_id": model_id,
            "status": "loading",
            "message": "Model loading started",
        }, status_code=202)


@lifecycle_router.post("/v1/models/{model_id:path}/unload", dependencies=[Depends(require_api_key)])
async def unload_model(model_id: str, force: bool = False) -> JSONResponse:
    """Unload a model from memory."""
    lifecycle = get_lifecycle_manager()
    
    status = lifecycle.get_status(model_id)
    if status == "unloaded":
        return JSONResponse({
            "model_id": model_id,
            "status": "unloaded",
            "message": "Model not loaded",
        })
    
    success = await lifecycle.unload_model(model_id, force=force)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot unload model (pinned or busy)",
        )
    
    return JSONResponse({
        "model_id": model_id,
        "status": "unloaded",
        "message": "Model unloaded",
    })


@lifecycle_router.get("/v1/models/loaded", dependencies=[Depends(require_api_key)])
async def list_loaded_models() -> JSONResponse:
    """List currently loaded models with memory usage."""
    lifecycle = get_lifecycle_manager()
    
    loaded = lifecycle.get_loaded_models()
    models = [LoadedModelInfo(**m) for m in loaded]
    
    return JSONResponse(jsonable_encoder(LoadedModelsResponse(models=models)))


@lifecycle_router.get("/v1/requests/{request_id}/status", dependencies=[Depends(require_api_key)])
async def get_request_status(request_id: str) -> JSONResponse:
    """Get the status and queue position of a request."""
    queue = get_queue_manager()
    
    request = queue.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    response = QueuePositionResponse(
        request_id=request_id,
        status=request.status,
        queue_position=request.queue_position if request.status == "queued" else None,
    )
    
    return JSONResponse(jsonable_encoder(response))


@lifecycle_router.post("/v1/requests/{request_id}/cancel", dependencies=[Depends(require_api_key)])
async def cancel_request(request_id: str) -> JSONResponse:
    """Cancel an in-flight or queued request."""
    queue = get_queue_manager()
    
    request = queue.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    cancelled = queue.cancel_request(request_id)
    
    response = CancelRequestResponse(
        request_id=request_id,
        cancelled=cancelled,
        status=request.status,
    )
    
    return JSONResponse(jsonable_encoder(response))
