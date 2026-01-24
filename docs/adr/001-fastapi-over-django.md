# ADR-001: FastAPI over Django

**Status**: Accepted
**Date**: January 23, 2026
**Context**: Choosing a Python web framework for the LLM API Gateway

## Decision
Use **FastAPI** as the primary web framework.

## Rationale
- **OpenAPI-first**: FastAPI auto-generates OpenAPI docs from type hints, reducing doc maintenance.
- **Async-friendly**: Native async/await support suits long-running inference and streaming responses.
- **Performance**: Starlette-based, faster than Django for I/O-bound workloads.
- **Flexibility**: No opinions on ORM/auth—allows SQLAlchemy/SQLModel and custom auth.
- **Simpler for API-only**: Django's admin/ORM/template features are unnecessary overhead for a pure API service.

## Alternatives Considered
- **Django + DRF**: More mature ecosystem, but heavier; async support is still catching up.
- **Flask**: Lightweight but lacks built-in OpenAPI and async.

## Consequences
- Must manually wire up ORM (SQLAlchemy/SQLModel) and migrations (Alembic).
- Auth must be implemented via dependencies (not batteries-included like Django).
- Team should be comfortable with Pydantic models and async patterns.

## Traceability
- Related to: SYS-REQ-001 (versioned HTTP API), INT-REQ-001 (OpenAPI contract)
