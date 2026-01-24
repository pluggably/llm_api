# Software Requirements — Backend Service

**Project**: Pluggably LLM API Gateway
**Component**: Backend Service (single deployable)
**Date**: January 24, 2026
**Status**: Complete (Baseline + CR-2026-01-24-02)

## User Stories

**Story ID**: US-001
**Title**: Standard multimodal API
**Priority**: High
**Story Points**: 8

As a developer
I want a standard HTTP API for text, image, and 3D generation
So that my clients can call one schema for multiple model types

**Acceptance Criteria**:
- [x] API exposes versioned endpoints for text, image, and 3D requests
- [x] Requests/Responses follow a consistent schema across modalities
- [x] OpenAPI documentation is generated

**Traceability**: SYS-REQ-001, SYS-REQ-004, INT-REQ-001

**Status**: Complete

---

**Story ID**: US-002
**Title**: Provider adapter integration
**Priority**: High
**Story Points**: 8

As a developer
I want pluggable provider adapters
So that I can connect to commercial, public, and local providers

**Acceptance Criteria**:
- [x] Adapter interface is defined and documented
- [x] At least one external provider adapter can be configured
- [x] Provider-specific errors map to standard error codes

**Traceability**: SYS-REQ-002, SYS-NFR-004

**Status**: Complete

---

**Story ID**: US-003
**Title**: Local model runner
**Priority**: High
**Story Points**: 8

As an operator
I want to run OSS text/image/3D models locally
So that I can use local inference without external API calls

**Acceptance Criteria**:
- [x] Local runner supports at least one OSS text model
- [x] Local runner supports at least one image or 3D model (if available)
- [x] Runner errors are surfaced via standard API errors

**Traceability**: SYS-REQ-003, SYS-REQ-004

**Status**: Complete

---

**Story ID**: US-004
**Title**: Model registry and download jobs
**Priority**: High
**Story Points**: 8

As an operator
I want to register and download models via the service
So that I can add models over time without redeploying

**Acceptance Criteria**:
- [x] Model registry stores metadata (name, version, modality, size, source)
- [x] Download jobs run asynchronously with status/progress
- [x] Downloads can be cancelled

**Traceability**: SYS-REQ-010, SYS-REQ-013, DATA-REQ-005

**Status**: Complete

---

**Story ID**: US-005
**Title**: Storage management
**Priority**: Medium
**Story Points**: 5

As an operator
I want storage policies for large model files
So that disk usage stays within safe limits

**Acceptance Criteria**:
- [x] Configurable max storage and retention policy
- [x] Cache cleanup job is available
- [x] Storage usage is visible via metrics or status endpoint

**Traceability**: SYS-REQ-012, SYS-NFR-007

**Status**: Complete

---

**Story ID**: US-006
**Title**: Per-request model selection
**Priority**: High
**Story Points**: 5

As a developer
I want to specify the model or approach in the request
So that I can choose different backends without changing endpoints

**Acceptance Criteria**:
- [x] Request schema includes a `model` selector field
- [x] Invalid model selections return validation errors
- [x] Default model can be configured

**Traceability**: SYS-REQ-011, DATA-REQ-004

**Status**: Complete

---

**Story ID**: US-007
**Title**: Auth and secure access
**Priority**: High
**Story Points**: 5

As an operator
I want multiple standard auth options
So that I can secure the API for local and cloud usage

**Acceptance Criteria**:
- [x] At least API key auth is supported
- [x] A second auth option is supported (e.g., OAuth/JWT) without stubs
- [x] Auth scheme is documented in OpenAPI

**Traceability**: SYS-REQ-014, INT-REQ-004

**Status**: Complete

---

**Story ID**: US-008
**Title**: Observability and metrics
**Priority**: Medium
**Story Points**: 3

As an operator
I want logs and metrics for requests
So that I can monitor usage and failures

**Acceptance Criteria**:
- [x] Structured logs include request IDs and latency
- [x] Basic metrics (requests, errors, latency) are exposed

**Traceability**: SYS-REQ-008, SYS-NFR-005

**Status**: Complete

---

**Story ID**: US-009
**Title**: Deployment guidance
**Priority**: Medium
**Story Points**: 3

As an operator
I want documentation to deploy on home server or cloud
So that I can run the system reliably

**Acceptance Criteria**:
- [x] Docs include local deployment instructions
- [x] Docs include cloud deployment guidance

**Traceability**: SYS-REQ-009

**Status**: Complete

---

**Story ID**: US-010
**Title**: Model catalog endpoint
**Priority**: High
**Story Points**: 5

As a developer
I want an endpoint that lists available models and capabilities
So that clients can discover what the system can run

**Acceptance Criteria**:
- [x] Endpoint returns model name, version, modality, and capabilities
- [x] Supports filtering by modality or provider
- [x] Response schema is documented in OpenAPI

**Traceability**: SYS-REQ-015, DATA-REQ-005, DATA-REQ-006

**Status**: Complete

---

**Story ID**: US-011
**Title**: Streaming responses (SSE)
**Priority**: High
**Story Points**: 5

As a developer
I want streaming text responses via SSE
So that clients receive partial results in real-time

**Acceptance Criteria**:
- [x] Request schema includes a `stream` boolean flag
- [x] SSE endpoint streams text tokens as they are generated
- [x] Streaming is documented in OpenAPI

**Traceability**: SYS-REQ-017, SYS-NFR-003

**Status**: Complete

---

**Story ID**: US-012
**Title**: Artifact store for large outputs
**Priority**: Medium
**Story Points**: 5

As a developer
I want large image/3D outputs returned as downloadable URLs
So that responses stay lightweight and clients can fetch artifacts separately

**Acceptance Criteria**:
- [x] Outputs exceeding size threshold are stored and returned as signed URLs
- [x] URLs expire after configurable TTL
- [x] Artifact store is pluggable (local disk or S3-compatible)

**Traceability**: SYS-REQ-016

**Status**: Complete

---

**Story ID**: US-013
**Title**: Auto-discover local models
**Priority**: High
**Story Points**: 5

As an operator
I want local model files to be auto-discovered
So that installed models appear in the catalog without manual registration

**Acceptance Criteria**:
- [x] On service startup, local model files under the configured model path are scanned
- [x] Discovered models appear in the model catalog with size, version (quantization), and local path
- [x] Discovery does not overwrite explicit registry entries

**Traceability**: SYS-REQ-018, DATA-REQ-005, DATA-REQ-006

**Status**: Complete

---

**Story ID**: US-014
**Title**: Parameter documentation endpoint
**Priority**: High
**Story Points**: 3

As a developer
I want to query parameter documentation from the API
So that I know what fields to send and how to use them

**Acceptance Criteria**:
- [x] API exposes an endpoint that returns parameter descriptions and examples
- [x] Documentation includes model selection guidance and supported values
- [x] Documentation is consistent with OpenAPI contract

**Traceability**: SYS-REQ-019, INT-REQ-005, DATA-REQ-007

**Status**: Complete

---

**Story ID**: US-015
**Title**: Session-aware generation
**Priority**: High
**Story Points**: 8

As a developer
I want to create a session and send multiple related requests
So that multi-turn interactions retain context across text, image, and 3D requests

**Acceptance Criteria**:
- [x] API supports creating a session and returning a session ID
- [x] Requests can reference a session ID to reuse context
- [x] Session context is appended per request with modality and outputs
- [x] Requests can optionally include provider/model state tokens for iterative updates

**Traceability**: SYS-REQ-020, DATA-REQ-008

**Status**: Complete

---

**Story ID**: US-016
**Title**: Session lifecycle management
**Priority**: High
**Story Points**: 5

As a developer
I want to list, reset, and close sessions
So that I can control and restart conversational context

**Acceptance Criteria**:
- [x] API supports listing sessions with metadata and last activity
- [x] API supports resetting a session context
- [x] API supports closing or archiving a session
- [x] Closed sessions preserve state tokens for audit (configurable retention)

**Traceability**: SYS-REQ-021, INT-REQ-006

**Status**: Complete

---

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
| SYS-REQ-016 | Backend | US-012 | Artifact store |
| SYS-REQ-017 | Backend | US-011 | Streaming |
| SYS-REQ-018 | Backend | US-013 | Model auto-discovery |
| SYS-REQ-019 | Backend | US-014 | Parameter documentation |
| SYS-REQ-020 | Backend | US-015 | Session management |
| SYS-REQ-021 | Backend | US-016 | Session lifecycle |
| SYS-REQ-022 | Backend | US-015, US-016 | Session state handoff |

## Definition of Ready / Done
**Ready**
- User stories written and traceable to system requirements.
- Acceptance criteria measurable.

**Done**
- User has reviewed and approved stories.
- Traceability matrix updated.
- All acceptance criteria are met and verified by tests.
