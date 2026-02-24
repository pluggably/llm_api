from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from llm_api.api.router import api_router
from llm_api.api.users_router import users_router
from llm_api.background_tasks import get_background_task_registry
from llm_api.api.lifecycle_router import lifecycle_router
from llm_api.config import get_settings
from llm_api.db import init_db
from llm_api.lifecycle import get_lifecycle_manager
from llm_api.observability import get_metrics_store
from llm_api.registry import get_registry
from llm_api.queue import get_queue_manager
from llm_api.runner.local_runner import clear_model_caches


def _configure_logging(settings) -> None:
    level = logging.DEBUG if settings.verbose_logs else getattr(
        logging, settings.log_level.upper(), logging.INFO
    )
    # basicConfig is a no-op when handlers already exist (e.g. uvicorn
    # configures the root logger before create_app runs), so we also set
    # the level explicitly on the root logger and every attached handler.
    logging.basicConfig(
        level=level,
        format="%(levelname)s:%(name)s:%(message)s",
    )
    root = logging.getLogger()
    root.setLevel(level)
    for handler in root.handlers:
        handler.setLevel(level)


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging(settings)
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        init_db()
        registry = get_registry()
        lifecycle = get_lifecycle_manager()
        
        # Load default/pinned models for each modality
        if settings.default_model:
            lifecycle.default_model_id = settings.default_model
        
        # Pin default image model (sdxl-turbo) for immediate availability
        if settings.default_image_model:
            lifecycle.pin_model(settings.default_image_model)
        
        # Start idle monitor
        await lifecycle.start_idle_monitor()
        
        yield
        
        try:
            # Shutdown — cancel/await background tasks with bounded waits so
            # Ctrl+C does not hang forever.
            await get_background_task_registry().shutdown(
                timeout=settings.shutdown_background_task_timeout_seconds,
            )
            await get_queue_manager().shutdown(
                timeout=settings.shutdown_queue_timeout_seconds,
            )
            await lifecycle.stop_idle_monitor(
                timeout=settings.shutdown_idle_monitor_timeout_seconds,
            )
        finally:
            # Always free model weights even if graceful shutdown timed out.
            clear_model_caches()
    
    app = FastAPI(
        title="Pluggably LLM API Gateway",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:50002",
            "http://127.0.0.1:50002",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    registry = get_registry()

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.time()
        metrics = get_metrics_store()
        metrics.record_request()
        try:
            response = await call_next(request)
        except Exception:
            metrics.record_error()
            raise
        finally:
            elapsed = (time.time() - start) * 1000
            metrics.record_latency(elapsed)
        if response.status_code >= 400:
            metrics.record_error()
        return response

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    @app.get("/ready")
    async def readiness_check():
        if registry.ready:
            return JSONResponse({"status": "ready"})
        return JSONResponse({"status": "not_ready"}, status_code=503)

    @app.get("/version")
    async def version_check():
        return {"version": settings.app_version}

    @app.get("/metrics")
    async def metrics():
        if not settings.metrics_enabled:
            return PlainTextResponse("metrics disabled", status_code=404)
        store = get_metrics_store()
        return PlainTextResponse(store.render_prometheus())

    # Lifecycle router must be included BEFORE api_router so that
    # /v1/models/loaded is registered before /v1/models/{model_id}
    app.include_router(lifecycle_router)
    app.include_router(api_router)
    app.include_router(users_router)

    return app


app = create_app()
