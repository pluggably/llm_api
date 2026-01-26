# Software Requirements — Client Library

**Project**: Pluggably LLM API Gateway + PlugAI Frontend
**Component**: Client Library
**Date**: January 26, 2026
**Status**: Updated (Pending Approval)

## User Stories

**Story ID**: US-CL-001
**Title**: Typed client for API endpoints
**Priority**: High
**Story Points**: 5

As a developer
I want typed client libraries for all API endpoints (Python and Dart/Flutter)
So that I can call the API without hand-crafting HTTP requests

**Acceptance Criteria**:
- [x] Python client exposes methods for all documented endpoints
- [x] Dart/Flutter client exposes methods for all documented endpoints
- [x] Request/response models are typed and validated in both clients
- [x] Errors are normalized with readable messages in both clients

**Traceability**: SYS-REQ-023, INT-REQ-008, DATA-REQ-010

**Status**: Complete

---

**Story ID**: US-CL-002
**Title**: Session helpers
**Priority**: High
**Story Points**: 3

As a developer
I want session helper methods in Python and Dart/Flutter clients
So that I can create, reset, and close sessions easily

**Acceptance Criteria**:
- [x] Helper methods wrap session endpoints in both clients
- [x] Helpers return typed session objects in both clients
- [x] Helpers propagate session errors clearly in both clients

**Traceability**: SYS-REQ-024, INT-REQ-006

**Status**: Complete

---

**Story ID**: US-CL-003
**Title**: User key management endpoints
**Priority**: Medium
**Story Points**: 3

As a developer
I want SDK methods to manage user provider and OSS keys
So that the PlugAI frontend can use the client SDK for key workflows

**Acceptance Criteria**:
- [ ] SDK exposes methods for provider key CRUD endpoints
- [ ] SDK exposes methods for OSS key creation/revocation endpoints
- [ ] Responses are typed and errors mapped

**Traceability**: SYS-REQ-035, SYS-REQ-036

**Status**: Not Started

---

**Story ID**: US-CL-004
**Title**: Auth and profile endpoints
**Priority**: Medium
**Story Points**: 3

As a developer
I want SDK methods for invite-only registration, login/logout, and profiles
So that the PlugAI frontend can use the client SDK for auth workflows

**Acceptance Criteria**:
- [ ] SDK exposes methods for invite-based registration
- [ ] SDK exposes login/logout and token handling helpers
- [ ] SDK exposes profile get/update methods

**Traceability**: SYS-REQ-037, SYS-REQ-038

**Status**: Not Started

---

**Story ID**: US-CL-005
**Title**: User API tokens endpoints
**Priority**: Medium
**Story Points**: 2

As a developer
I want SDK methods to create and revoke user API tokens
So that the frontend can manage tokens via the SDK

**Acceptance Criteria**:
- [ ] SDK exposes token create/list/revoke methods
- [ ] Token values returned only on creation
- [ ] Errors mapped consistently

**Traceability**: SYS-REQ-039

**Status**: Not Started

---

**Story ID**: US-CL-006
**Title**: Model download status and progress
**Priority**: Medium
**Story Points**: 3

As a developer
I want SDK methods to query model download status and progress
So that the frontend can display download state

**Acceptance Criteria**:
- [ ] SDK exposes method to get model status (downloading/ready/failed)
- [ ] SDK exposes method to get download progress for active downloads
- [ ] SDK optionally supports SSE/WebSocket subscription for real-time updates

**Traceability**: SYS-REQ-042, SYS-REQ-043

**Status**: Not Started

---

**Story ID**: US-CL-007
**Title**: Prepare/load model
**Priority**: High
**Story Points**: 2

As a developer
I want SDK methods to pre-load a model into memory
So that I can avoid cold-start latency

**Acceptance Criteria**:
- [ ] SDK exposes loadModel(modelId) method
- [ ] Returns loading status or completion
- [ ] Supports async/await pattern

**Traceability**: SYS-REQ-049

**Status**: Not Started

---

**Story ID**: US-CL-008
**Title**: Model runtime status query
**Priority**: High
**Story Points**: 2

As a developer
I want SDK methods to query model runtime status
So that I know if a model is ready for requests

**Acceptance Criteria**:
- [ ] SDK exposes getModelRuntimeStatus(modelId) method
- [ ] Returns status: unloaded, loading, loaded, busy
- [ ] Includes queue depth if busy

**Traceability**: SYS-REQ-050

**Status**: Not Started

---

**Story ID**: US-CL-009
**Title**: Get loaded models
**Priority**: Medium
**Story Points**: 2

As a developer
I want SDK methods to list currently loaded models
So that I can monitor system state

**Acceptance Criteria**:
- [ ] SDK exposes getLoadedModels() method
- [ ] Returns list with memory usage and load time

**Traceability**: SYS-REQ-051

**Status**: Not Started

---

**Story ID**: US-CL-010
**Title**: Request cancellation
**Priority**: High
**Story Points**: 3

As a developer
I want SDK methods to cancel in-flight requests
So that I can implement cancel buttons

**Acceptance Criteria**:
- [ ] SDK exposes cancelRequest(requestId) method
- [ ] Request is aborted and resources freed
- [ ] Confirmation returned

**Traceability**: SYS-REQ-047

**Status**: Not Started

---

**Story ID**: US-CL-011
**Title**: Request queueing status
**Priority**: Medium
**Story Points**: 2

As a developer
I want SDK methods to query queue position
So that I can show wait indicators

**Acceptance Criteria**:
- [ ] SDK exposes getQueuePosition(requestId) method
- [ ] Returns position and estimated wait
- [ ] Optionally supports SSE subscription

**Traceability**: SYS-REQ-046

**Status**: Not Started

---

**Story ID**: US-CL-012
**Title**: Hugging Face model search
**Priority**: Medium
**Story Points**: 3

As a developer
I want SDK methods to search Hugging Face models
So that the frontend can add models via the API

**Acceptance Criteria**:
- [ ] SDK exposes `searchModels(query, source="huggingface")`
- [ ] Results include model id, name, tags, modality hints
- [ ] Pagination tokens are surfaced

**Traceability**: SYS-REQ-063

**Status**: Not Started

---

**Story ID**: US-CL-013
**Title**: Session metadata support
**Priority**: Medium
**Story Points**: 2

As a developer
I want session models to include title and timestamps
So that the UI can show session names and message timing

**Acceptance Criteria**:
- [ ] Session list parsing supports `{sessions: [...]}` shape
- [ ] Session models include `title`, `created_at`, `last_used_at`
- [ ] Message models include `created_at`

**Traceability**: SYS-REQ-065, SYS-REQ-066, SYS-REQ-067

**Status**: Not Started

---

**Story ID**: US-CL-014
**Title**: Health check helper
**Priority**: Low
**Story Points**: 1

As a developer
I want an SDK method to call the health endpoint
So that the UI can show a connection test result

**Acceptance Criteria**:
- [ ] SDK exposes `getHealth()`
- [ ] Returns status string or throws on failure

**Traceability**: SYS-REQ-068

**Status**: Not Started

---

## Traceability
System → Software

| System Req ID | Software Component | User Story ID(s) | Notes |
|---|---|---|---|
| SYS-REQ-023 | Client Library | US-CL-001 | Typed SDK |
| SYS-REQ-024 | Client Library | US-CL-002 | Session helpers |
| SYS-REQ-035 | Client Library | US-CL-003 | User provider keys |
| SYS-REQ-036 | Client Library | US-CL-003 | User OSS keys |
| SYS-REQ-037 | Client Library | US-CL-004 | Auth/profile helpers |
| SYS-REQ-038 | Client Library | US-CL-004 | Auth/profile helpers |
| SYS-REQ-039 | Client Library | US-CL-005 | User API tokens |
| SYS-REQ-042 | Client Library | US-CL-006 | Download status |
| SYS-REQ-043 | Client Library | US-CL-006 | Model status |
| SYS-REQ-046 | Client Library | US-CL-011 | Queue status |
| SYS-REQ-047 | Client Library | US-CL-010 | Request cancellation |
| SYS-REQ-049 | Client Library | US-CL-007 | Prepare/load model |
| SYS-REQ-050 | Client Library | US-CL-008 | Model runtime status |
| SYS-REQ-051 | Client Library | US-CL-009 | Get loaded models |
| SYS-REQ-063 | Client Library | US-CL-012 | Hugging Face search |
| SYS-REQ-065 | Client Library | US-CL-013 | Sessions list parsing |
| SYS-REQ-066 | Client Library | US-CL-013 | Session naming metadata |
| SYS-REQ-067 | Client Library | US-CL-013 | Message timestamps |
| SYS-REQ-068 | Client Library | US-CL-014 | Health check helper |

## Definition of Ready / Done
**Ready**
- User stories written and traceable to system requirements.
- Acceptance criteria measurable.

**Done**
- User has reviewed and approved stories.
- Traceability matrix updated.
- All acceptance criteria are met and verified by tests.
