# Software Requirements — Backend Service

**Project**: Pluggably LLM API Gateway + PlugAI Frontend
**Component**: Backend Service (single deployable)
**Date**: January 26, 2026
**Status**: Updated (Pending Approval)

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

**Story ID**: US-035
**Title**: Session update endpoint
**Priority**: Medium
**Story Points**: 2

As a developer
I want to update session metadata via a PUT endpoint
So that clients can rename or update session fields

**Acceptance Criteria**:
- [x] API supports `PUT /v1/sessions/{session_id}`
- [x] Request accepts optional `title`
- [x] Response returns updated session object

**Traceability**: SYS-REQ-060

**Status**: Complete

---

**Story ID**: US-036
**Title**: Sessions list contract
**Priority**: High
**Story Points**: 3

As a developer
I want the sessions list endpoint to return a consistent JSON shape
So that clients can reliably render the left-pane sessions list

**Acceptance Criteria**:
- [ ] `GET /v1/sessions` returns `{ "sessions": [...] }`
- [ ] Each session includes id, title (nullable), last_used_at, created_at
- [ ] Response schema documented in OpenAPI

**Traceability**: SYS-REQ-065

**Status**: Not Started

---

## DoR/DoD Checklist
- [ ] Ready: US-043 captured with acceptance criteria and traceability.
- [ ] Done: Backend requirements reviewed for SYS-REQ-071–075 alignment.

---

**Story ID**: US-037
**Title**: Session naming support
**Priority**: Medium
**Story Points**: 3

As a developer
I want sessions to support titles
So that users can name and find conversations

**Acceptance Criteria**:
- [ ] Session create accepts optional `title`
- [ ] Session update persists `title`
- [ ] Session list and get endpoints return `title`

**Traceability**: SYS-REQ-066

**Status**: Not Started

---

**Story ID**: US-038
**Title**: Session message timestamps
**Priority**: Medium
**Story Points**: 3

As a developer
I want messages to store timestamps
So that clients can display prompt/response timing

**Acceptance Criteria**:
- [ ] Session messages include `created_at` timestamps
- [ ] Session history returns timestamps for prompts and outputs
- [ ] Timestamps are timezone-aware ISO 8601

**Traceability**: SYS-REQ-067

**Status**: Not Started

---

**Story ID**: US-039
**Title**: Hugging Face model search endpoint
**Priority**: High
**Story Points**: 5

As a developer
I want an API endpoint to search Hugging Face for models
So that the UI can add new models from a catalog

**Acceptance Criteria**:
- [ ] `GET /v1/models/search` accepts `query`, `source=huggingface`, and optional `modality`
- [ ] Response includes model id, name, tags, modality hints, and download source
- [ ] Results are paginated

**Traceability**: SYS-REQ-063

**Status**: Not Started

---

**Story ID**: US-040
**Title**: Provider credential types
**Priority**: High
**Story Points**: 5

As a developer
I want provider credential storage to support multiple auth types
So that commercial providers can be configured correctly per user

**Acceptance Criteria**:
- [ ] Credential records store provider + credential type
- [ ] Supported types include API key, endpoint+key, OAuth token, service account JSON
- [ ] Credentials are encrypted at rest and never logged

**Traceability**: SYS-REQ-064, SYS-NFR-012

**Status**: Not Started

---

**Story ID**: US-041
**Title**: Health check endpoint for UI
**Priority**: Medium
**Story Points**: 1

As a developer
I want a simple health endpoint for connectivity testing
So that the UI can show a green check on success

**Acceptance Criteria**:
- [x] `GET /health` returns `{status: "ok"}`
- [ ] Endpoint is documented for UI use

**Traceability**: SYS-REQ-068

**Status**: In Progress

---

**Story ID**: US-042
**Title**: Auto model selection routing
**Priority**: High
**Story Points**: 5

As a developer
I want the router to resolve a model when `model` is omitted or set to `auto`
So that clients can send prompts without pre-selecting a model

**Acceptance Criteria**:
- [ ] `model` may be omitted or set to `auto`
- [ ] Rule-based resolver selects a model by inferred modality and prompt intent
- [ ] Selection can be constrained with `selection_mode` (`auto | free_only | commercial_only | model`)
- [ ] Resolved model ID is returned in the response
- [ ] If no model is available, return a clear error

**Traceability**: SYS-REQ-CR003-001, SYS-REQ-CR003-002, SYS-REQ-CR003-004
**Traceability**: SYS-REQ-CR003-001, SYS-REQ-CR003-002, SYS-REQ-CR003-004, SYS-REQ-CR003-005

**Status**: Not Started

---

**Story ID**: US-017
**Title**: Persistent model registry
**Priority**: High
**Story Points**: 5

As an operator
I want model metadata and schemas persisted in SQLite
So that the registry survives restarts and can migrate to a cloud database

**Acceptance Criteria**:
- [ ] Models, schemas, and capabilities persist across restarts
- [ ] Database migrations are versioned and repeatable
- [ ] Registry export/import supports migration to Postgres/Supabase

**Traceability**: SYS-REQ-033, SYS-NFR-013

**Status**: Not Started

---

**Story ID**: US-018
**Title**: Schema registry synchronization
**Priority**: High
**Story Points**: 3

As a developer
I want `/v1/schema` to reflect registry-stored parameter schemas
So that clients can render accurate dynamic settings

**Acceptance Criteria**:
- [ ] `/v1/schema` is backed by stored schema definitions
- [ ] Schema versions are tracked per model
- [ ] Updates to registry schemas are reflected in the API response

**Traceability**: SYS-REQ-034

**Status**: Not Started

---

**Story ID**: US-043
**Title**: Provider model discovery and credits/quota reporting
**Priority**: High
**Story Points**: 8

As a developer
I want the backend to discover accessible commercial models and credit status per user
So that the UI can show available models and warn when premium credits are exhausted

**Acceptance Criteria**:
- [ ] On startup and when provider keys change, the system queries provider APIs for accessible models per user
- [ ] Results are cached and rate-limited to avoid provider throttling
- [ ] `/v1/models` includes discovered provider models when a user has valid credentials
- [ ] API responses include provider credit/usage status when available
- [ ] Model selection uses available credits/quota when choosing a model
- [ ] API indicates when premium credits are exhausted and the system has switched to a free-tier model
- [ ] Requests may specify a provider/vendor instead of a model ID and the backend selects a suitable model
- [ ] Logs never include secrets or raw credential payloads

**Traceability**: SYS-REQ-071, SYS-REQ-072, SYS-REQ-073, SYS-REQ-075, SYS-NFR-021, SYS-NFR-022, INT-REQ-013, INT-REQ-014, DATA-REQ-015, DATA-REQ-016
**Status**: Not Started

---

**Story ID**: US-019
**Title**: Per-user provider API keys
**Priority**: Medium
**Story Points**: 5

As a user
I want to store my own provider API keys
So that I can use my accounts for commercial models

**Acceptance Criteria**:
- [ ] API allows create/list/update/delete of user provider keys
- [ ] Keys are encrypted at rest and never logged
- [ ] Requests can use user-scoped keys when configured

**Traceability**: SYS-REQ-035, SYS-NFR-012

**Status**: Not Started

---

**Story ID**: US-020
**Title**: User OSS access keys
**Priority**: Medium
**Story Points**: 5

As a user
I want to create and revoke OSS access keys
So that I can share limited access to local models

**Acceptance Criteria**:
- [ ] API allows creation and revocation of OSS access keys
- [ ] Keys are scoped and revocable
- [ ] Requests with revoked keys are denied

**Traceability**: SYS-REQ-036, SYS-NFR-012

**Status**: Not Started

---

**Story ID**: US-021
**Title**: Invite-only authentication
**Priority**: High
**Story Points**: 5

As an operator
I want invite-only registration and authentication
So that access is limited to approved users

**Acceptance Criteria**:
- [ ] Registration requires a valid invite token
- [ ] Login issues an auth token (JWT/session)
- [ ] Logout revokes/invalidates the token

**Traceability**: SYS-REQ-037

**Status**: Not Started

---

**Story ID**: US-022
**Title**: User profiles and preferences
**Priority**: Medium
**Story Points**: 3

As a user
I want preferences stored in my profile
So that the frontend can load my default models and settings

**Acceptance Criteria**:
- [ ] Profile CRUD endpoints available
- [ ] Preferences stored per user and returned with profile
- [ ] Defaults applied for preferred model selection

**Traceability**: SYS-REQ-038

**Status**: Not Started

---

**Story ID**: US-023
**Title**: User API tokens
**Priority**: Medium
**Story Points**: 3

As a user
I want to create and revoke private API tokens
So that I can call the API directly

**Acceptance Criteria**:
- [ ] API supports create/list/revoke of user tokens
- [ ] Tokens are stored hashed and only shown once on creation
- [ ] Token auth is accepted in place of the default API key

**Traceability**: SYS-REQ-039

**Status**: Not Started

---

**Story ID**: US-024
**Title**: Hugging Face model documentation enrichment
**Priority**: Medium
**Story Points**: 3

As an operator
I want model entries enriched with Hugging Face documentation and parameter guidance
So that users understand how to use each model

**Acceptance Criteria**:
- [ ] When registering a HF model, metadata and model card content are fetched
- [ ] Parameter guidance is stored when available
- [ ] Failures to fetch docs do not block model registration

**Traceability**: SYS-REQ-040, SYS-NFR-016

**Status**: Not Started

---

**Story ID**: US-025
**Title**: Background model downloads with status and dedupe
**Priority**: High
**Story Points**: 5

As an operator
I want model downloads to run asynchronously with status and reuse
So that the API/UI remain responsive and duplicate downloads are avoided

**Acceptance Criteria**:
- [ ] Downloads run in background workers and do not block API responses
- [ ] Model list exposes status: downloading/ready/failed
- [ ] Repeated download requests reuse existing artifacts or in-progress jobs

**Traceability**: SYS-REQ-042, SYS-REQ-043, SYS-REQ-044

**Status**: Not Started

---

**Story ID**: US-026
**Title**: Model lifecycle management
**Priority**: High
**Story Points**: 8

As an operator
I want to configure model lifecycle (idle timeout, pinning, concurrent limits)
So that memory usage is optimized and predictable

**Acceptance Criteria**:
- [ ] Models unload after configurable idle timeout
- [ ] Pinned models remain loaded and never auto-unload
- [ ] Concurrent loaded models are limited by configuration
- [ ] LRU eviction when limit is reached

**Traceability**: SYS-REQ-045

**Status**: Not Started

---

**Story ID**: US-027
**Title**: Request queueing
**Priority**: High
**Story Points**: 5

As a user
I want requests to queue when inference resources are busy
So that requests don't fail due to resource contention

**Acceptance Criteria**:
- [ ] Requests queue when model/GPU is busy
- [ ] Queue position is returned in response headers or body
- [ ] Queue updates are available via polling or SSE
- [ ] Configurable max queue depth

**Traceability**: SYS-REQ-046

**Status**: Not Started

---

**Story ID**: US-028
**Title**: Request cancellation
**Priority**: High
**Story Points**: 5

As a user
I want to cancel in-flight generation requests
So that I can stop long-running or unwanted requests

**Acceptance Criteria**:
- [ ] API exposes cancel endpoint with request_id
- [ ] Cancellation stops inference and frees resources
- [ ] Response indicates cancellation status
- [ ] Partial results optionally returned

**Traceability**: SYS-REQ-047

**Status**: Not Started

---

**Story ID**: US-029
**Title**: Regenerate/retry responses
**Priority**: Medium
**Story Points**: 3

As a user
I want to regenerate a response with same or modified parameters
So that I can get alternative outputs

**Acceptance Criteria**:
- [ ] API accepts regenerate request referencing original request_id or session turn
- [ ] Parameters can be overridden for regeneration
- [ ] New response replaces or appends to session history (configurable)

**Traceability**: SYS-REQ-048

**Status**: Not Started

---

**Story ID**: US-030
**Title**: Prepare/load model endpoint
**Priority**: High
**Story Points**: 5

As a developer
I want to pre-load a model into memory before making requests
So that I avoid cold-start latency

**Acceptance Criteria**:
- [ ] API exposes POST /v1/models/{id}/load endpoint
- [ ] Returns immediately with loading status
- [ ] Status can be polled via model runtime status
- [ ] Load respects concurrent model limits (queues or errors)

**Traceability**: SYS-REQ-049

**Status**: Not Started

---

**Story ID**: US-031
**Title**: Model runtime status
**Priority**: High
**Story Points**: 3

As a developer
I want to query model runtime status (unloaded/loading/loaded/busy)
So that I know if a model is ready for requests

**Acceptance Criteria**:
- [ ] GET /v1/models/{id} includes runtime_status field
- [ ] Status values: unloaded, loading, loaded, busy
- [ ] Busy includes queue depth if applicable

**Traceability**: SYS-REQ-050

**Status**: Not Started

---

**Story ID**: US-032
**Title**: Get loaded models endpoint
**Priority**: Medium
**Story Points**: 2

As an operator
I want to list currently loaded models
So that I can monitor memory usage

**Acceptance Criteria**:
- [ ] GET /v1/models/loaded returns list of loaded models
- [ ] Includes memory usage estimate per model
- [ ] Includes load time and last used time

**Traceability**: SYS-REQ-051

**Status**: Not Started

---

**Story ID**: US-033
**Title**: Default pinned model
**Priority**: High
**Story Points**: 3

As an operator
I want a default model always loaded and available
So that users have immediate response while other models load

**Acceptance Criteria**:
- [ ] Default model loads on startup
- [ ] Default model never auto-unloads
- [ ] Requests can specify "use default while loading" behavior
- [ ] Default model configurable per modality

**Traceability**: SYS-REQ-052

**Status**: Not Started

---

**Story ID**: US-034
**Title**: Fallback model configuration
**Priority**: Medium
**Story Points**: 5

As an operator
I want to configure fallback chains for models
So that requests succeed even if primary model fails

**Acceptance Criteria**:
- [ ] Fallback chain configurable per model or globally
- [ ] Chain tries models in order until success
- [ ] Response indicates which model actually served the request
- [ ] Fallback used during cold-start of primary model

**Traceability**: SYS-REQ-053

**Status**: Not Started

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
| SYS-REQ-033 | Backend | US-017 | Registry persistence |
| SYS-REQ-034 | Backend | US-018 | Schema registry sync |
| SYS-REQ-035 | Backend | US-019 | User provider keys |
| SYS-REQ-036 | Backend | US-020 | User OSS keys |
| SYS-REQ-037 | Backend | US-021 | Invite-only auth |
| SYS-REQ-038 | Backend | US-022 | User profiles/preferences |
| SYS-REQ-039 | Backend | US-023 | User API tokens |
| SYS-REQ-040 | Backend | US-024 | HF documentation enrichment |
| SYS-REQ-042 | Backend | US-025 | Async downloads |
| SYS-REQ-043 | Backend | US-025 | Model status |
| SYS-REQ-044 | Backend | US-025 | Download dedupe |
| SYS-REQ-045 | Backend | US-026 | Model lifecycle |
| SYS-REQ-046 | Backend | US-027 | Request queueing |
| SYS-REQ-047 | Backend | US-028 | Request cancellation |
| SYS-REQ-048 | Backend | US-029 | Regenerate/retry |
| SYS-REQ-049 | Backend | US-030 | Prepare/load model |
| SYS-REQ-050 | Backend | US-031 | Model runtime status |
| SYS-REQ-051 | Backend | US-032 | Get loaded models |
| SYS-REQ-052 | Backend | US-033 | Default pinned model |
| SYS-REQ-053 | Backend | US-034 | Fallback configuration |
| SYS-REQ-060 | Backend | US-035 | Session update endpoint |
| SYS-REQ-063 | Backend | US-039 | Hugging Face search |
| SYS-REQ-064 | Backend | US-040 | Provider credential types |
| SYS-REQ-065 | Backend | US-036 | Sessions list contract |
| SYS-REQ-066 | Backend | US-037 | Session naming |
| SYS-REQ-067 | Backend | US-038 | Message timestamps |
| SYS-REQ-068 | Backend | US-041 | Health check endpoint |
| SYS-REQ-CR003-001 | Backend | US-042 | Auto model selection |
| SYS-REQ-CR003-002 | Backend | US-042 | Rule-based resolver |
| SYS-REQ-CR003-004 | Backend | US-042 | Manual override preserved |
| SYS-REQ-CR003-005 | Backend | US-042 | Selection mode filters |

## Definition of Ready / Done
**Ready**
- User stories written and traceable to system requirements.
- Acceptance criteria measurable.

**Done**
- User has reviewed and approved stories.
- Traceability matrix updated.
- All acceptance criteria are met and verified by tests.
