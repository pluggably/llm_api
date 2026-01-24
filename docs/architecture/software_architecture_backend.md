# Software Architecture — Backend Service

**Project**: Pluggably LLM API Gateway
**Component**: Backend Service (single deployable)
**Date**: January 24, 2026
**Status**: Approved (Baseline + CR-2026-01-24-02)

## Overview
This document defines the software architecture for the backend service, including module structure, interfaces between modules, and key interaction flows.

## Component Diagram (Mermaid)
```mermaid
graph LR
    API[API Layer]
    Auth[Auth Module]
    Router[Request Router]
    Adapters[Provider Adapters]
    Runner[Local Model Runner]
    Registry[Model Registry]
    Downloader[Download Jobs]
    Storage[Storage Manager]
    Config[Config Manager]
    Obs[Observability]
    Sessions[Session Manager]
    DB[(Metadata DB)]

    API --> Auth
    API --> Router
    API --> Obs
    Router --> Adapters
    Router --> Runner
    Router --> Sessions
    Runner --> Registry
    Registry --> Downloader
    Registry --> DB
    Downloader --> Storage
    Runner --> Storage
    API --> Config
    API --> Sessions
```

## Module/Package Structure
- `api/`: FastAPI app, routing, request/response schemas
- `auth/`: auth middleware/dependencies (API key, JWT/OAuth stubs)
- `router/`: backend selection logic, model routing
- `adapters/`: provider adapters (commercial/public)
- `runner/`: local OSS model execution
- `registry/`: model registry, capabilities, catalog endpoints
- `jobs/`: download tasks, job status tracking
- `storage/`: storage limits, cache/retention policies
- `config/`: env/config file loading
- `observability/`: logging, metrics, tracing
- `sessions/`: session store and history management
- `db/`: metadata persistence (models, jobs, tokens)

## Interface Definitions (Module-Level)
- **API → Auth**: dependency injection for auth; returns user/token context
- **API → Router**: standardized request object → routing decision + execution
- **Router → Adapters**: provider call interface
- **Router → Runner**: local execution interface
- **Registry → DB**: CRUD model metadata, capabilities
- **Jobs → Storage**: download/cleanup operations
- **API → Registry**: list models, register/download endpoints
- **API → Registry**: model detail lookup for catalog and discovery results
- **API → Sessions**: create/list/update/close session APIs
- **Router → Sessions**: append messages and fetch session context

## Sequence Diagrams (Mermaid)

### Text/Image/3D Request Flow
```mermaid
sequenceDiagram
    participant C as Client
    participant API as API Layer
    participant Auth as Auth
    participant Router as Router
    participant Adapters as Provider Adapter
    participant Runner as Local Runner

    C->>API: POST /v1/generate
    API->>Auth: authenticate
    Auth-->>API: auth context
    API->>Router: route(request)
    alt External provider
        Router->>Adapters: call provider
        Adapters-->>Router: provider response
    else Local model
        Router->>Runner: run model
        Runner-->>Router: local response
    end
    Router-->>API: normalized response
    API-->>C: 200 + response
```

### Model Download Job Flow
```mermaid
sequenceDiagram
    participant Admin as Operator
    participant API as API Layer
    participant Registry as Registry
    participant Jobs as Download Jobs
    participant Storage as Storage Manager

    Admin->>API: POST /v1/models/download
    API->>Registry: create model entry
    Registry-->>API: model id
    API->>Jobs: enqueue download
    Jobs->>Storage: download model
    Storage-->>Jobs: progress updates
    Jobs-->>Registry: update status
    API-->>Admin: job id

```

### Startup Model Discovery Flow
```mermaid
sequenceDiagram
    participant App as Application
    participant Registry as Registry
    participant Storage as Model Storage

    App->>Registry: load defaults
    Registry->>Storage: scan model path for local files
    Storage-->>Registry: list of local model files
    Registry-->>Registry: register discovered models
```

### Session Request Flow
```mermaid
sequenceDiagram
    participant C as Client
    participant API as API Layer
    participant Router as Router
    participant Sessions as Session Manager
    participant Runner as Local Runner

    C->>API: POST /v1/sessions/{id}/generate
    API->>Router: route(request)
    Router->>Sessions: load session context
    Router->>Runner: run with context
    Runner-->>Router: response
    Router->>Sessions: append response
    Router-->>API: normalized response
    API-->>C: 200 + response
```

## Technology & Framework Choices (Draft)
- **Framework**: FastAPI (async, OpenAPI generation)
- **DB**: SQLite initially (upgradeable to Postgres)
- **Jobs**: Background task queue (RQ/Celery) or built-in async tasks
- **ORM**: SQLAlchemy/SQLModel
- **Auth**: API key + JWT/OAuth (configurable)

## Design Patterns
- Adapter pattern for providers
- Strategy pattern for routing/model selection
- Repository pattern for registry/data access

## Error Handling
- Standardized error codes and messages across modules
- Map provider errors to internal error types
- Return validation errors for bad inputs

## Traceability
System → Software

| System Req ID | Software Component | User Story ID(s) | Notes |
|---|---|---|---|
| SYS-REQ-001 | Backend | US-001 | |
| SYS-REQ-002 | Backend | US-002 | |
| SYS-REQ-003 | Backend | US-003 | |
| SYS-REQ-004 | Backend | US-001, US-003 | |
| SYS-REQ-005 | Backend | US-001, US-006 | |
| SYS-REQ-006 | Backend | US-002 | |
| SYS-REQ-007 | Backend | US-001 | |
| SYS-REQ-008 | Backend | US-008 | |
| SYS-REQ-009 | Backend | US-009 | |
| SYS-REQ-010 | Backend | US-004 | |
| SYS-REQ-011 | Backend | US-006 | |
| SYS-REQ-012 | Backend | US-005 | |
| SYS-REQ-013 | Backend | US-004 | |
| SYS-REQ-014 | Backend | US-007 | |
| SYS-REQ-015 | Backend | US-010 | |
| SYS-REQ-018 | Backend | US-013 | Model auto-discovery |
| SYS-REQ-019 | Backend | US-014 | Parameter documentation |
| SYS-REQ-020 | Backend | US-015 | Session management |
| SYS-REQ-021 | Backend | US-016 | Session lifecycle |

## Definition of Ready / Done
**Ready**
- Modules identified and interfaces defined.
- Diagrams render correctly.

**Done**
- Interface contracts implemented for key endpoints.
- Traceability matrix updated.
- Reviewed and approved by user.
