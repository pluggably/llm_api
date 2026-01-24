from __future__ import annotations

import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from llm_api.api.router import api_router
from llm_api.config import get_settings
from llm_api.observability import get_metrics_store
from llm_api.registry import get_registry


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Pluggably LLM API Gateway", version="0.1.0")

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

    @app.get("/metrics")
    async def metrics():
        if not settings.metrics_enabled:
            return PlainTextResponse("metrics disabled", status_code=404)
        store = get_metrics_store()
        return PlainTextResponse(store.render_prometheus())

    app.include_router(api_router)

    return app


app = create_app()
