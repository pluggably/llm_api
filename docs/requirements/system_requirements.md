# System Requirements

**Project**: Pluggably LLM API Gateway + Cross-Platform Frontend (PlugAI)
**Date**: January 24, 2026
**Status**: Updated (Pending Approval)

## Assumptions
- The standard API will be HTTP-based and JSON by default.
- The system will run on macOS/Linux class hosts (home server) and common cloud providers.
- GPU acceleration is optional but supported when available.
- SQLite is the initial persistence layer; schema must be migratable to a cloud database (e.g., Supabase/Postgres).

## Out of Scope
- Training new foundation models from scratch.

## Functional Requirements (System)
- **SYS-REQ-001**: Provide a versioned HTTP API that accepts standardized requests for text, image, and 3D generation.
- **SYS-REQ-002**: Support configurable backend adapters for commercial APIs, free/public APIs (if available), and local OSS models.
- **SYS-REQ-003**: Provide a local model runner subsystem capable of running selected OSS text, image, and 3D models.
- **SYS-REQ-004**: Support non-text generation (image, 3D) via standardized endpoints or explicitly versioned extensions.
- **SYS-REQ-005**: Provide a routing/selection mechanism to choose backend per request (by config, user, or request parameter).
- **SYS-REQ-006**: Provide configuration management for API keys, endpoints, and local model paths.
- **SYS-REQ-007**: Provide health checks and readiness endpoints.
- **SYS-REQ-008**: Provide usage logging and basic metrics.
- **SYS-REQ-009**: Provide documentation for local and cloud deployment.
- **SYS-REQ-010**: Provide a model registry/management mechanism to download, register, and update OSS models over time.
- **SYS-REQ-011**: Allow API requests to specify desired model and/or inference approach (with validation).
- **SYS-REQ-012**: Provide storage management for local models (capacity checks, configurable cache/retention policies, cleanup tools).
- **SYS-REQ-013**: Support long-running model download jobs with status/progress reporting and cancellation.
- **SYS-REQ-014**: Require API authentication and authorization with configurable support for multiple standard auth modes (e.g., API key, OAuth/JWT, local-only mode).
- **SYS-REQ-015**: Provide an API endpoint to list available models and their capabilities.
- **SYS-REQ-016**: Provide artifact storage for large outputs (images, 3D meshes) with signed, expiring download URLs.
- **SYS-REQ-017**: Support streaming responses (SSE) for text generation requests.
- **SYS-REQ-018**: Automatically discover locally installed model files in storage and register them in the model catalog.
- **SYS-REQ-019**: Provide a queryable API schema/parameter documentation endpoint for request parameters and model selection guidance.
- **SYS-REQ-020**: Provide session management to associate multiple requests with a persistent conversational context.
- **SYS-REQ-021**: Provide APIs to create, retrieve, list, update, and close sessions, including the ability to reset session context.
- **SYS-REQ-022**: Support both backend-stored session state and client-supplied state tokens for iterative generation workflows.
- **SYS-REQ-054**: Persist all session state (including chat history, context, and metadata) independently of model process lifecycle, ensuring sessions survive model spindown/unload and can be resumed after model reload.
- **SYS-REQ-023**: Provide client libraries (Python and Dart/Flutter) with typed request/response models for all API endpoints.
- **SYS-REQ-024**: Provide session helper utilities in each client library for create/reset/close flows.
- **SYS-REQ-025**: Provide a cross-platform frontend UI (web + mobile) that integrates with the standard API.
- **SYS-REQ-026**: Provide model selection UI with modality filtering (text/image/3D) and model metadata display.
- **SYS-REQ-027**: Render a dynamic settings pane/drawer based on `/v1/schema` for the selected model.
- **SYS-REQ-028**: Provide a chat-like interface for text models with streaming response rendering.
- **SYS-REQ-029**: Provide an image generation UI with gallery, preview, and download support.
- **SYS-REQ-030**: Provide a 3D generation UI with interactive viewer and download support.
- **SYS-REQ-031**: Allow the web frontend to be hosted separately from the backend with configurable API base URL.
- **SYS-REQ-032**: Provide frontend-driven session creation and switching, with per-user context preserved across turns.
- **SYS-REQ-033**: Persist a model registry for internal and external models, including supported parameters and schemas.
- **SYS-REQ-034**: Store and serve model parameter schemas from the registry, synchronized with `/v1/schema`.
- **SYS-REQ-035**: Allow users to supply and manage their own commercial provider API keys, stored securely per user.
- **SYS-REQ-036**: Allow users to create and manage API keys for OSS model access, scoped and revocable.
- **SYS-REQ-037**: Provide user authentication with login/logout and invite-only registration.
- **SYS-REQ-038**: Provide user profiles with preferences (preferred models, UI defaults) stored per user.
- **SYS-REQ-039**: Allow users to create, list, and revoke private API tokens for LLM API access.
- **SYS-REQ-040**: Enrich model registry entries with Hugging Face documentation and parameter guidance when available.
- **SYS-REQ-041**: Support UI layout auto-switching by modality/device with user override (auto/locked/manual).
- **SYS-REQ-042**: Model downloads must run asynchronously and not block API or UI requests.
- **SYS-REQ-043**: Provide model status states (e.g., downloading, ready, failed) in model listings.
- **SYS-REQ-044**: Prevent duplicate downloads by reusing existing model artifacts across users.
- **SYS-REQ-045**: Provide model lifecycle management with configurable idle timeout, pinning, and concurrent loaded model limits.
- **SYS-REQ-046**: Provide request queueing when local inference resources are busy, with queue position feedback.
- **SYS-REQ-047**: Support cancellation of in-flight generation requests.
- **SYS-REQ-048**: Support regenerating a response with same or modified parameters.
- **SYS-REQ-049**: Provide a prepare/load model endpoint to pre-load a model into memory before requests.
- **SYS-REQ-050**: Provide model runtime status (unloaded, loading, loaded, busy) in model queries.
- **SYS-REQ-051**: Provide an endpoint to list currently loaded models.
- **SYS-REQ-052**: Support a default "pinned" model that remains loaded and can serve as an optional fallback during cold-start of other models.
- **SYS-REQ-053**: Allow users to choose (via API parameter or frontend option) whether to fall back to a default/pinned model while the requested model is loading, or to wait for the requested model.
- **SYS-REQ-055**: Align authentication endpoints for client SDKs with backend implementation (`/v1/users/register`, `/v1/users/login`).
- **SYS-REQ-056**: Align generation endpoint and schema for client SDKs (`/v1/generate` with `{model, modality, input, parameters?, stream?}`).
- **SYS-REQ-057**: Align lifecycle endpoints to include `model_id` in path (`/v1/models/{model_id}/status|load|unload`).
- **SYS-REQ-058**: Align request management endpoints to use plural form (`/v1/requests/{request_id}/status|cancel`).
- **SYS-REQ-059**: Align user resource endpoints to `/v1/users/tokens` and `/v1/users/provider-keys` (no `/me` prefix).
- **SYS-REQ-060**: Provide session update endpoint (`PUT /v1/sessions/{session_id}`).
- **SYS-REQ-061**: Maintain a comprehensive API endpoint reference document for consumers.
- **SYS-REQ-062**: Frontend must use the shared Dart client package (`clients/dart`) for API calls.

## Non-Functional Requirements (System)
- **SYS-NFR-001**: Secure secret storage for provider API keys (no secrets in logs).
- **SYS-NFR-002**: Provide clear, consistent error responses with error codes.
- **SYS-NFR-003**: Support streaming responses if enabled (SSE or WebSocket) with bounded resource usage.
- **SYS-NFR-004**: Modular adapter architecture to add providers without breaking the API.
- **SYS-NFR-005**: Observability: structured logs and basic metrics for requests, latency, and errors.
- **SYS-NFR-006**: Performance budgets (TBD): define p95 latency and throughput targets per deployment type.
- **SYS-NFR-007**: Disk usage must be bounded by configurable limits to protect host stability.
- **SYS-NFR-008**: Support TLS for API traffic when deployed in networked environments.
- **SYS-NFR-009**: Cross-platform UI support (web + mobile) with responsive layouts.
- **SYS-NFR-010**: UI responsiveness for model selection and parameter updates (<100ms).
- **SYS-NFR-011**: Accessibility support for the frontend (WCAG AA where applicable).
- **SYS-NFR-012**: Per-user credential isolation; keys encrypted at rest and never logged.
- **SYS-NFR-013**: Model registry persistence; survives restarts and supports migrations.
- **SYS-NFR-014**: Auth must enforce invite-only registration and protect all user-specific data.
- **SYS-NFR-015**: User API tokens must be securely stored and revocable.
- **SYS-NFR-016**: Model documentation enrichment must not block model registration if external data is unavailable.
- **SYS-NFR-017**: Background downloads must not degrade API responsiveness beyond defined latency budgets.
- **SYS-NFR-018**: Request queue must provide position updates within 1 second of state change.
- **SYS-NFR-019**: Model loading/unloading must be graceful and not interrupt in-flight requests.
- **SYS-NFR-020**: Default pinned model must load on startup and remain available.

## External Interface Requirements
- **INT-REQ-001**: API contract must be documented (OpenAPI preferred) with versioning and error schemas.
- **INT-REQ-002**: If streaming is supported, provide SSE/WebSocket contract.
- **INT-REQ-003**: Provide a minimal client example for the standard API.
- **INT-REQ-004**: Document supported authentication schemes and required headers/tokens.
- **INT-REQ-005**: Provide an API endpoint that returns parameter documentation and usage examples.
- **INT-REQ-006**: Provide session management endpoints and document them in the OpenAPI contract.
- **INT-REQ-007**: Document how clients can supply or omit session state tokens per request.
- **INT-REQ-008**: Provide client library documentation and versioning aligned with the API contract (Python and Dart/Flutter).

## Data Requirements
- **DATA-REQ-001**: Define request/response schemas for text, image, and 3D generation.
- **DATA-REQ-002**: Support provider-specific metadata without breaking the standard response.
- **DATA-REQ-003**: Log request metadata without storing full prompts by default (configurable).
- **DATA-REQ-004**: Include a standardized model selection field in requests.
- **DATA-REQ-005**: Maintain a model registry schema (name, version, modality, source, size, hardware requirements).
- **DATA-REQ-006**: Store model capabilities metadata (supported modalities, context limits, output formats, required hardware).
- **DATA-REQ-007**: Provide a machine-readable schema for request parameters and model selection guidance.
- **DATA-REQ-008**: Store session metadata and message history (modality, inputs, outputs, timestamps) with configurable retention.
- **DATA-REQ-009**: Represent provider/model state tokens in a standard field with passthrough support.
- **DATA-REQ-010**: Share request/response schemas between server and client to ensure compatibility.

## Error Modes
- For unsupported model features, return a standardized “feature not supported” error.
- For backend provider failure, return a standardized “backend unavailable” error with retry guidance.
- For invalid input, return a standardized “validation error” with field-level details.

## System Constraints
- Must run on a single machine (home server) without requiring a cluster.
- Must also be deployable to cloud environments with minimal changes.
- Use SQLite for v1 persistence (model registry, user keys, sessions).
- Provide migration path to Supabase/Postgres without breaking API contracts.

## Definition of Ready / Done
**Ready**
- SYS-REQ IDs assigned and traceability started.
- Assumptions and out-of-scope documented.
- Key NFRs captured with placeholders for metrics.

**Done**
- Each system requirement is testable and traced to at least one test spec.
- Interface contracts drafted and implemented.
- Automated tests pass for all traced requirements.

## Traceability
Stakeholder → System

| Stakeholder Req ID | System Req ID(s) | Notes |
|---|---|---|
| SH-REQ-001 | SYS-REQ-001, SYS-REQ-005 | |
| SH-REQ-002 | SYS-REQ-002, SYS-REQ-006 | |
| SH-REQ-003 | SYS-REQ-003 | |
| SH-REQ-004 | SYS-REQ-004 | |
| SH-REQ-005 | SYS-REQ-010 | |
| SH-REQ-006 | SYS-REQ-011 | |
| SH-REQ-007 | SYS-REQ-009 | |
| SH-REQ-008 | SYS-REQ-009 | |
| SH-REQ-009 | SYS-REQ-008 | |
| SH-REQ-010 | SYS-REQ-012 | |
| SH-REQ-011 | SYS-REQ-013 | |
| SH-REQ-012 | SYS-REQ-014 | |
| SH-REQ-013 | SYS-REQ-015 | |
| SH-REQ-014 | SYS-REQ-017 | Streaming |
| SH-REQ-015 | SYS-REQ-016 | Artifact store |
| SH-REQ-016 | SYS-REQ-018 | Model auto-discovery |
| SH-REQ-017 | SYS-REQ-019 | Parameter documentation |
| SH-REQ-018 | SYS-REQ-020 | Session management |
| SH-REQ-019 | SYS-REQ-021 | Session lifecycle |
| SH-REQ-020 | SYS-REQ-022 | Session state handoff |
| SH-REQ-021 | SYS-REQ-023 | Client library |
| SH-REQ-022 | SYS-REQ-024 | Session helpers |
| SH-REQ-023 | SYS-REQ-025 | Cross-platform UI |
| SH-REQ-024 | SYS-REQ-026 | Model selection UI |
| SH-REQ-025 | SYS-REQ-027 | Dynamic parameters |
| SH-REQ-026 | SYS-REQ-028 | Chat UI |
| SH-REQ-027 | SYS-REQ-029, SYS-REQ-030 | Image/3D UI |
| SH-REQ-028 | SYS-REQ-031 | Separate hosting |
| SH-REQ-029 | SYS-REQ-032 | Frontend sessions |
| SH-REQ-030 | SYS-REQ-033, SYS-REQ-034 | Model registry |
| SH-REQ-031 | SYS-REQ-035 | User provider keys |
| SH-REQ-032 | SYS-REQ-036 | User OSS keys |
| SH-REQ-033 | SYS-REQ-037 | Auth & invite-only registration |
| SH-REQ-034 | SYS-REQ-038 | User profiles/preferences |
| SH-REQ-035 | SYS-REQ-039 | User API tokens |
| SH-REQ-036 | SYS-REQ-040 | Model documentation enrichment |
| SH-REQ-037 | SYS-REQ-041 | UI auto-switch/lock |
| SH-REQ-038 | SYS-REQ-042, SYS-REQ-043, SYS-REQ-044 | Background downloads, status, dedupe |
| SH-REQ-039 | SYS-REQ-045, SYS-REQ-050, SYS-REQ-051, SYS-REQ-052 | Model lifecycle |
| SH-REQ-040 | SYS-REQ-049 | Pre-load models |
| SH-REQ-041 | SYS-REQ-046 | Request queueing |
| SH-REQ-042 | SYS-REQ-047 | Request cancellation |
| SH-REQ-043 | SYS-REQ-048 | Regenerate/retry |
| SH-REQ-044 | SYS-REQ-052, SYS-REQ-053 | Fallback configuration |
| SH-REQ-045 | SYS-REQ-055, SYS-REQ-056, SYS-REQ-057, SYS-REQ-058, SYS-REQ-059, SYS-REQ-060 | Endpoint alignment |
| SH-REQ-046 | SYS-REQ-061 | API endpoint reference |
| SH-REQ-047 | SYS-REQ-062 | Shared Dart client usage |

Requirements → Verification

| Requirement ID | Verification Type | Test/Procedure ID | Location | Notes |
|---|---|---|---|---|
| SYS-REQ-001 | Automated | TEST-SYS-001, TEST-UNIT-001 | tests/system/, tests/unit/ | |
| SYS-REQ-002 | Automated | TEST-INT-001 | tests/integration/ | |
| SYS-REQ-003 | Automated | TEST-SYS-001 | tests/system/ | |
| SYS-REQ-004 | Automated | TEST-SYS-001 | tests/system/ | |
| SYS-REQ-005 | Automated | TEST-UNIT-002 | tests/unit/ | |
| SYS-REQ-006 | Automated | TEST-UNIT-005 | tests/unit/ | |
| SYS-REQ-007 | Automated | TEST-SYS-004 | tests/system/ | |
| SYS-REQ-008 | Automated | TEST-SYS-005 | tests/system/ | |
| SYS-REQ-009 | Manual | TEST-MAN-004 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-010 | Automated | TEST-SYS-003 | tests/system/ | |
| SYS-REQ-011 | Automated | TEST-UNIT-002 | tests/unit/ | |
| SYS-REQ-012 | Automated | TEST-INT-002, TEST-UNIT-004 | tests/integration/, tests/unit/ | |
| SYS-REQ-013 | Automated | TEST-SYS-003 | tests/system/ | |
| SYS-REQ-014 | Automated | TEST-UNIT-003 | tests/unit/ | |
| SYS-REQ-015 | Automated | TEST-SYS-002 | tests/system/ | |
| SYS-REQ-016 | Automated | TEST-SYS-006 | tests/system/ | Artifact store |
| SYS-REQ-017 | Automated | TEST-SYS-007 | tests/system/ | Streaming |
| SYS-REQ-018 | Automated | TEST-SYS-010 | tests/system/ | Auto-discovery |
| SYS-REQ-019 | Automated | TEST-SYS-011 | tests/system/ | Schema endpoint |
| SYS-REQ-020 | Automated | TEST-SYS-012 | tests/system/ | Sessions |
| SYS-REQ-021 | Automated | TEST-SYS-013 | tests/system/ | Session lifecycle |
| SYS-REQ-022 | Automated | TEST-SYS-014 | tests/system/ | Session state tokens |
| SYS-REQ-023 | Automated | TEST-UNIT-006 | client/tests/unit/ | SDK models |
| SYS-REQ-024 | Automated | TEST-UNIT-007 | client/tests/unit/ | Session helpers |
| SYS-REQ-025 | Manual | TEST-MAN-004 | docs/testing/manual_test_procedures.md | UI availability |
| SYS-REQ-026 | Manual | TEST-MAN-004 | docs/testing/manual_test_procedures.md | Model selection |
| SYS-REQ-027 | Manual | TEST-MAN-004 | docs/testing/manual_test_procedures.md | Dynamic parameters |
| SYS-REQ-028 | Manual | TEST-MAN-005 | docs/testing/manual_test_procedures.md | Chat UI |
| SYS-REQ-029 | Manual | TEST-MAN-006 | docs/testing/manual_test_procedures.md | Image UI |
| SYS-REQ-030 | Manual | TEST-MAN-007 | docs/testing/manual_test_procedures.md | 3D UI |
| SYS-REQ-031 | Manual | TEST-MAN-008 | docs/testing/manual_test_procedures.md | Separate hosting |
| SYS-REQ-032 | Manual | TEST-MAN-009 | docs/testing/manual_test_procedures.md | Frontend sessions |
| SYS-REQ-033 | Automated | TEST-INT-005 | tests/integration/ | Model registry persistence |
| SYS-REQ-034 | Automated | TEST-INT-006 | tests/integration/ | Schema registry sync |
| SYS-REQ-035 | Manual | TEST-MAN-010 | docs/testing/manual_test_procedures.md | User provider keys |
| SYS-REQ-036 | Manual | TEST-MAN-011 | docs/testing/manual_test_procedures.md | User OSS keys |
| SYS-REQ-037 | Manual | TEST-MAN-012 | docs/testing/manual_test_procedures.md | Invite-only auth |
| SYS-REQ-038 | Manual | TEST-MAN-013 | docs/testing/manual_test_procedures.md | User profiles/preferences |
| SYS-REQ-039 | Manual | TEST-MAN-014 | docs/testing/manual_test_procedures.md | User API tokens |
| SYS-REQ-040 | Automated | TEST-INT-007 | tests/integration/ | Model doc enrichment |
| SYS-REQ-041 | Manual | TEST-MAN-015 | docs/testing/manual_test_procedures.md | UI auto-switch/lock |
| SYS-REQ-042 | Automated | TEST-INT-008 | tests/integration/ | Async downloads |
| SYS-REQ-043 | Automated + Manual | TEST-INT-009, TEST-MAN-016 | tests/integration/, docs/testing/manual_test_procedures.md | Model status |
| SYS-REQ-044 | Automated | TEST-INT-010 | tests/integration/ | Download dedupe |
| SYS-REQ-045 | Automated | TEST-INT-011 | tests/integration/ | Model lifecycle |
| SYS-REQ-046 | Automated | TEST-INT-012, TEST-SYS-015 | tests/integration/, tests/system/ | Request queueing |
| SYS-REQ-047 | Automated | TEST-SYS-016 | tests/system/ | Request cancellation |
| SYS-REQ-048 | Manual | TEST-MAN-017 | docs/testing/manual_test_procedures.md | Regenerate/retry |
| SYS-REQ-049 | Automated | TEST-INT-013 | tests/integration/ | Prepare/load model |
| SYS-REQ-050 | Automated | TEST-INT-014 | tests/integration/ | Model runtime status |
| SYS-REQ-051 | Automated | TEST-INT-015 | tests/integration/ | Get loaded models |
| SYS-REQ-052 | Automated | TEST-INT-016 | tests/integration/ | Default pinned model |
| SYS-REQ-053 | Automated | TEST-INT-017 | tests/integration/ | Fallback configuration |
| SYS-REQ-054 | Automated | TEST-SYS-017 | tests/system/ | Session survives model spindown |
| SYS-REQ-055 | Automated | TEST-INT-CR001-001 | frontend/test/sdk/api_client_test.dart | Auth endpoints |
| SYS-REQ-056 | Automated | TEST-INT-CR001-002 | frontend/test/sdk/api_client_test.dart | Generate endpoint/schema |
| SYS-REQ-057 | Automated | TEST-INT-CR001-003 | frontend/test/sdk/api_client_test.dart | Lifecycle endpoints |
| SYS-REQ-058 | Automated | TEST-INT-CR001-004 | frontend/test/sdk/api_client_test.dart | Request endpoints |
| SYS-REQ-059 | Automated | TEST-INT-CR001-005 | frontend/test/sdk/api_client_test.dart | User resource endpoints |
| SYS-REQ-060 | Automated | TEST-INT-CR001-006 | src/llm_api/api/router.py | Session update endpoint |
| SYS-REQ-061 | Manual | TEST-MAN-CR001-001 | docs/api_endpoints.md | API reference review |
| SYS-REQ-062 | Manual | TEST-MAN-CR002-001 | docs/testing/manual_test_procedures.md | Frontend uses shared Dart client |
