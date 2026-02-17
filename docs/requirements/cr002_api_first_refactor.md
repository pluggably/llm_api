# Change Request CR-002: API-First Responsibility Refactor

**Date**: February 17, 2026
**Status**: Approved (with changes incorporated — image preprocessing is model-driven, not arbitrary)
**Scope**: Architectural (affects backend API, client library, frontend, and interface contracts)

## Problem

The API is the primary programmatic interface — any consumer (curl, Python script, mobile app) should get a complete, robust experience without relying on client-side logic. An audit of the frontend revealed six categories of business logic that have leaked into the Flutter frontend or are missing from the backend/client library:

1. **Session auto-naming**: The frontend truncates the first prompt to 50 chars + date and calls `updateSession()`. Any API consumer must replicate this or sessions remain unnamed.
2. **Image preprocessing**: The frontend resizes images to max 1024px edge, re-encodes to PNG, and validates size before sending. An API consumer sending a raw 4K image gets no preprocessing — the model may reject it or OOM.
3. **Regeneration orchestration**: The frontend manually finds the last user message, removes the last assistant message, and re-sends. There is no API operation for "regenerate last response."
4. **Artifact URL resolution**: The frontend manually prepends `baseUrl` to relative artifact paths. API consumers receive incomplete paths.
5. **First-message detection**: The frontend tracks whether a session is new to decide when to auto-name. The backend doesn't expose this state.
6. **Legacy client duplication**: Two parallel Dart client implementations (`LlmApiClient` in `api_client.dart` and `PluggablyClient` in `pluggably_client.dart`) with duplicated model classes.

## Proposed Solution

### Change 1: Backend auto-titles sessions on first message
- When the backend appends the first user message to a session that has no title, it auto-generates a title from the message content (truncated, cleaned).
- The frontend and any API consumer get auto-titled sessions for free.
- Clients can still override via `PUT /v1/sessions/{id}`.

### Change 2: Backend auto-resizes image inputs to match model requirements
- The `/v1/generate` endpoint accepts raw image data (base64 data-URLs or artifact references) and automatically preprocesses images to match the target model's requirements before passing to inference:
  - Look up the target model's image input constraints (max resolution, accepted formats, aspect ratio rules) from the model registry or provider metadata.
  - Decode → resize to fit the model's actual input requirements → re-encode in the format the model expects.
  - If the model has no documented constraints, pass through unchanged (no arbitrary resize).
  - Return a warning header or field if the image was resized.
- This makes the API robust for any consumer, not just the frontend.
- The frontend can remove its image preprocessing pipeline entirely.

### Change 3: Backend `POST /v1/sessions/{id}/regenerate` endpoint
- New endpoint that replays the last user message, replacing the last assistant response.
- Accepts optional parameter overrides (model, temperature, etc.).
- Returns the new response (streaming or non-streaming).
- The frontend calls one method instead of orchestrating message surgery.

### Change 4: Backend returns fully-qualified artifact URLs
- All artifact URLs in `GenerateResponse` are returned as absolute URLs (including scheme + host).
- No client-side URL assembly required.

### Change 5: Backend tracks `message_count` on sessions
- The `SessionRecord` exposes a `message_count` field in API responses.
- Auto-naming triggers internally on first message — no client-side detection needed.
- This change is mostly internal; the field is informational for API consumers.

### Change 6: Consolidate Dart client into single implementation
- Merge `ApiError` and any unique types from `pluggably_client.dart` into `api_client.dart` / `models.dart`.
- Remove `pluggably_client.dart`.
- Update the frontend's single import to use the consolidated package.

### Change 7: Frontend cleanup
- Remove auto-naming logic from `chat_page.dart`.
- Remove image preprocessing pipeline from `chat_page.dart` (send raw images, let backend handle it).
- Remove regeneration orchestration from `chat_page.dart` (call new endpoint).
- Remove artifact URL prefixing from `chat_page.dart`.
- Add a `regenerate()` helper to the Dart client library.

## Impact Assessment

| Layer | Files Affected | Impact |
|---|---|---|
| Backend API | `router.py` | New regenerate endpoint, image preprocessing, auto-naming, absolute URLs |
| Backend sessions | `store.py` | Auto-naming on first message, message_count |
| Backend runner | `local_runner.py` | Accept raw images (preprocessing step) |
| Client (Dart) | `api_client.dart`, `models.dart`, `pluggably_client.dart` | Consolidation, new `regenerate()` method, model updates |
| Client (Python) | `llm_api_client/` | New `regenerate()` method (if exists) |
| Frontend | `chat_page.dart` | Remove business logic (auto-naming, image resize, regeneration, URL assembly) |
| OpenAPI contract | `openapi.yaml` | New endpoint, updated response schemas |
| Docs | Multiple | Architecture, design, API endpoints docs |
| Tests | `tests/unit/`, `tests/system/`, `clients/dart/test/` | New tests for all changes |

## Alternatives Considered

1. **Image resize in client library only**: Rejected — API consumers using curl/Python still get no preprocessing. Backend is the right layer since the backend knows the model's capabilities.
2. **Keep regeneration in client library**: Partially viable, but the backend can do it atomically (no race conditions with concurrent writes to the same session). Backend endpoint is cleaner.
3. **Keep auto-naming in client**: Rejected — every consumer would need to implement the same policy. Backend is the single source of truth.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Image resize adds latency to generation requests | Medium | Low | Resize only when image exceeds the specific model's limits; pass through unchanged otherwise; no processing when model has no documented constraints |
| Breaking change for existing API consumers | Low | Medium | Artifact URLs are currently relative (undocumented) — making them absolute is additive. New endpoint is additive. Auto-naming is transparent. |
| Frontend regression after removing logic | Medium | Medium | Keep frontend logic until backend is verified working end-to-end |
| Legacy client removal breaks imports | Low | Low | Only one import (`ApiError`) — consolidate before removing |

---

## New/Updated Requirements

### New Stakeholder Requirements

**SH-REQ-055**: The API must preprocess image inputs (resize, re-encode) as needed to match the target model's specific input requirements, so any API consumer can send raw images without knowing model constraints.

**SH-REQ-056**: The API must auto-name sessions when the first message is sent, without requiring client action.

**SH-REQ-057**: The API must provide a single-call regeneration operation that replaces the last assistant response.

**SH-REQ-058**: The API must return fully-qualified artifact URLs that are directly usable without client-side assembly.

### New System Requirements

**SYS-REQ-071**: The backend must automatically preprocess image inputs in generation requests to match the target model's requirements: decode base64 data-URLs, look up the model's image input constraints (max resolution, accepted format) from the model registry or provider metadata, resize and re-encode as needed. If the model has no documented image constraints, images are passed through unchanged. If the image already meets the model's requirements, no processing occurs.

**SYS-REQ-072**: When the first user message is appended to a session that has no title, the backend must auto-generate a title from the message content (first 50 characters of text, trimmed).

**SYS-REQ-073**: Provide a `POST /v1/sessions/{session_id}/regenerate` endpoint that replaces the last assistant response by replaying the last user message. The endpoint must accept optional parameter overrides and support streaming responses.

**SYS-REQ-074**: All artifact URLs in generation responses must be returned as absolute URLs (scheme + host + path), directly usable by any consumer without URL assembly.

**SYS-REQ-075**: Session API responses must include a `message_count` integer field.

**SYS-REQ-076**: The Dart client library must be consolidated into a single client class (`LlmApiClient`) with no duplicate model definitions. The legacy `PluggablyClient` class must be removed.

### Updated System Requirements

**SYS-REQ-048** (existing — regenerate/retry): Now satisfied by the new `POST /v1/sessions/{id}/regenerate` endpoint, not by client-side orchestration.

**SYS-REQ-070** (existing — image inputs): Extended to include backend-side preprocessing so the API is self-contained.

### New Software Requirements (Backend)

**Story ID**: US-042
**Title**: Model-driven image preprocessing
**Priority**: High
**Story Points**: 5

As an API consumer
I want the backend to preprocess my image inputs to match the target model's requirements
So that I can send raw images without needing to know each model's constraints

**Acceptance Criteria**:
- [ ] Images in `input.images[]` are decoded from base64 data-URLs
- [ ] The target model's image input constraints (max resolution, accepted format) are looked up from the model registry or provider metadata
- [ ] Images exceeding the model's constraints are resized preserving aspect ratio and re-encoded in the model's expected format
- [ ] Images that already meet the model's constraints are passed through unchanged
- [ ] If the model has no documented image constraints, images are passed through unchanged (no arbitrary resize)
- [ ] A `warnings` field in the response indicates if images were resized, including the original and new dimensions
- [ ] The preprocessing runs before images are sent to the inference backend

**Traceability**: SYS-REQ-071, SYS-REQ-070

**Status**: Not Started

---

**Story ID**: US-043
**Title**: Session auto-naming on first message
**Priority**: Medium
**Story Points**: 2

As an API consumer
I want sessions to get a readable name automatically
So that I don't need to implement naming logic in every client

**Acceptance Criteria**:
- [ ] When the first user-role message is appended to a session with no title, the backend auto-generates a title
- [ ] Title is the first 50 characters of the message text, trimmed of whitespace
- [ ] If the session already has a title, it is not overwritten
- [ ] Clients can still override the title via `PUT /v1/sessions/{id}`

**Traceability**: SYS-REQ-072, SYS-REQ-066

**Status**: Not Started

---

**Story ID**: US-044
**Title**: Regenerate endpoint
**Priority**: High
**Story Points**: 5

As an API consumer
I want to call a single endpoint to regenerate the last response
So that I don't need to orchestrate message removal and replay client-side

**Acceptance Criteria**:
- [ ] `POST /v1/sessions/{session_id}/regenerate` replays the last user message
- [ ] The last assistant message is replaced with the new response
- [ ] Optional `model`, `parameters`, `stream` overrides are accepted
- [ ] Streaming (SSE) is supported when `stream: true`
- [ ] Returns 404 if session does not exist
- [ ] Returns 400 if session has no messages to regenerate

**Traceability**: SYS-REQ-073, SYS-REQ-048

**Status**: Not Started

---

**Story ID**: US-045
**Title**: Absolute artifact URLs
**Priority**: Medium
**Story Points**: 2

As an API consumer
I want artifact URLs in responses to be absolute
So that I can use them directly without knowing the server's base URL

**Acceptance Criteria**:
- [ ] `image_artifact_urls` and `artifact_3d_url` in `GenerateResponse` are absolute URLs
- [ ] URLs include scheme, host, and port derived from the current request
- [ ] Relative paths are no longer returned

**Traceability**: SYS-REQ-074, SYS-REQ-016

**Status**: Not Started

---

**Story ID**: US-046
**Title**: Session message count
**Priority**: Low
**Story Points**: 1

As an API consumer
I want to see a message count in session responses
So that I can determine session state without loading full message history

**Acceptance Criteria**:
- [ ] `message_count` integer field is included in session list and detail responses
- [ ] Count reflects the number of messages currently in the session

**Traceability**: SYS-REQ-075

**Status**: Not Started

---

### New Software Requirements (Client Library)

**Story ID**: US-CL-010
**Title**: Client library consolidation
**Priority**: High
**Story Points**: 3

As a developer
I want a single Dart client class with no duplicate models
So that I have one canonical import for all API operations

**Acceptance Criteria**:
- [ ] `ApiError` is defined in the main client package (not in a legacy file)
- [ ] `pluggably_client.dart` is removed
- [ ] All imports in the frontend are updated to the consolidated package
- [ ] No duplicate model class definitions remain

**Traceability**: SYS-REQ-076, SYS-REQ-023

**Status**: Not Started

---

**Story ID**: US-CL-011
**Title**: Regenerate helper method
**Priority**: Medium
**Story Points**: 2

As a developer
I want a `regenerate()` method on the Dart and Python clients
So that I can call regeneration with one method

**Acceptance Criteria**:
- [ ] Dart client exposes `regenerate(sessionId, {model?, parameters?, stream?})`
- [ ] Streaming variant returns `Stream<GenerationStreamEvent>`
- [ ] Non-streaming variant returns `GenerationResponse`
- [ ] Python client exposes equivalent method (if Python client exists and is maintained)

**Traceability**: SYS-REQ-073, SYS-REQ-024

**Status**: Not Started

---

### Frontend Cleanup (not a new requirement — implements existing requirements correctly)

**Story ID**: US-FE-020
**Title**: Remove leaked business logic from frontend
**Priority**: High
**Story Points**: 3

As a maintainer
I want the frontend to delegate business logic to the API
So that the API is the complete, authoritative interface

**Acceptance Criteria**:
- [ ] Auto-naming logic removed from `chat_page.dart` (backend handles it)
- [ ] Image preprocessing (resize/re-encode) removed from `chat_page.dart` (backend handles it)
- [ ] Regeneration orchestration removed; replaced with single `client.regenerate()` call
- [ ] Artifact URL prefixing removed (backend returns absolute URLs)
- [ ] Import of `pluggably_client.dart` replaced with consolidated package import

**Traceability**: SYS-REQ-062, SYS-REQ-071, SYS-REQ-072, SYS-REQ-073, SYS-REQ-074

**Status**: Not Started

---

## Updated Traceability

### Stakeholder → System (new entries)

| Stakeholder Req ID | System Req ID(s) | Notes |
|---|---|---|
| SH-REQ-055 | SYS-REQ-071, SYS-REQ-070 | Image preprocessing in backend |
| SH-REQ-056 | SYS-REQ-072, SYS-REQ-066 | Auto-naming |
| SH-REQ-057 | SYS-REQ-073, SYS-REQ-048 | Regenerate endpoint |
| SH-REQ-058 | SYS-REQ-074, SYS-REQ-016 | Absolute artifact URLs |

### System → Software (new entries)

| System Req ID | Software Component | User Story ID(s) | Notes |
|---|---|---|---|
| SYS-REQ-071 | Backend | US-042 | Image preprocessing |
| SYS-REQ-072 | Backend | US-043 | Session auto-naming |
| SYS-REQ-073 | Backend, Client | US-044, US-CL-011 | Regenerate endpoint + client helper |
| SYS-REQ-074 | Backend | US-045 | Absolute artifact URLs |
| SYS-REQ-075 | Backend | US-046 | Message count |
| SYS-REQ-076 | Client | US-CL-010 | Client consolidation |

### Requirements → Verification (planned)

| Requirement ID | Verification Type | Test/Procedure ID | Location | Notes |
|---|---|---|---|---|
| SYS-REQ-071 | Automated | TEST-UNIT-020, TEST-SYS-020 | tests/unit/, tests/system/ | Image resize logic + end-to-end |
| SYS-REQ-072 | Automated | TEST-UNIT-021, TEST-SYS-021 | tests/unit/, tests/system/ | Auto-naming logic |
| SYS-REQ-073 | Automated | TEST-UNIT-022, TEST-SYS-022 | tests/unit/, tests/system/ | Regenerate endpoint |
| SYS-REQ-074 | Automated | TEST-UNIT-023 | tests/unit/ | Absolute URL generation |
| SYS-REQ-075 | Automated | TEST-UNIT-024 | tests/unit/ | Message count field |
| SYS-REQ-076 | Automated | TEST-UNIT-025 | clients/dart/test/ | Single client class |
| US-FE-020 | Manual | TEST-MAN-020 | docs/testing/manual_test_procedures.md | Frontend cleanup verification |

---

## Approval Request

This change request affects interfaces, data models, and design across backend, client library, and frontend. Per agents.md, explicit approval is required before implementation proceeds.

**Please review and respond with:**
- `APPROVED: CR-002` to proceed with all changes
- `APPROVED: CR-002 (partial)` with specific items to proceed with a subset
- `CHANGES REQUESTED: <feedback>` for modifications
