# Software Requirements: PlugAI Frontend

**Project**: Pluggably LLM API Gateway + Cross-Platform Frontend (PlugAI)
**Date**: January 26, 2026
**Status**: Updated (Pending Approval)

## Overview
This document specifies the software requirements for the PlugAI frontend application. It relies on the Dart client SDK to communicate with the LLM API and implements UI flows for model selection, chat sessions, and modality-specific generation.

## User Stories

**Story ID**: US-FE-001
**Title**: Model catalog and modality filtering
**Priority**: High
**Story Points**: 5

As a user
I want to browse models grouped by modality
So that I can quickly select the right model for my task

**Acceptance Criteria**:
- [x] Models are loaded from `/v1/models` via the Dart client
- [x] Tabs filter by text/image/3D
- [x] Each model card shows name, provider, and version

**Traceability**: SYS-REQ-025, SYS-REQ-026
**Status**: Complete

---

**Story ID**: US-FE-002
**Title**: Model selection updates UI
**Priority**: High
**Story Points**: 3

As a user
I want the UI to update when I select a model
So that I always see the correct settings and interaction pattern

**Acceptance Criteria**:
- [x] Selecting a model updates the active modality
- [x] Selecting a model triggers schema fetch for that model
- [ ] The main panel switches to chat/image/3D layout based on modality

**Traceability**: SYS-REQ-026, SYS-REQ-027
**Status**: In Progress

---

**Story ID**: US-FE-003
**Title**: Dynamic parameter panel
**Priority**: High
**Story Points**: 8

As a user
I want a settings pane that shows only the parameters for the selected model
So that I can configure generation without guessing

**Acceptance Criteria**:
- [x] Parameters are rendered from `/v1/schema` via the Dart client
- [x] Supported field types include text, number, slider, enum, and boolean
- [x] Defaults are applied from schema
- [ ] Validation errors are shown inline

**Traceability**: SYS-REQ-027
**Status**: In Progress

---

**Story ID**: US-FE-004
**Title**: Text chat UI with streaming
**Priority**: High
**Story Points**: 8

As a user
I want a chat interface for text models
So that I can hold multi-turn conversations

**Acceptance Criteria**:
- [x] Chat bubbles display user and assistant messages
- [x] Streaming responses render incrementally
- [x] Markdown is rendered in responses
- [x] Send button disabled while a request is in-flight

**Traceability**: SYS-REQ-028, SYS-REQ-032
**Status**: Complete

---

**Story ID**: US-FE-005
**Title**: Image generation UI
**Priority**: High
**Story Points**: 5

As a user
I want a gallery view for image generations
So that I can view and download results

**Acceptance Criteria**:
- [x] Gallery shows generated images for the current session using artifact URLs
- [x] Loading placeholder shown while awaiting response
- [x] Download action is available per image (saves original file)
- [x] Clicking an image opens a larger preview

**Traceability**: SYS-REQ-029
**Status**: Testing

---

**Story ID**: US-FE-006
**Title**: 3D generation UI
**Priority**: Medium
**Story Points**: 8

As a user
I want a 3D preview for 3D outputs
So that I can inspect results before download

**Acceptance Criteria**:
- [x] 3D viewer renders the mesh artifact and supports rotate/zoom
- [x] Download action is available for the mesh artifact (OBJ)
- [x] Viewer shows a loading state and error message on failure

**Traceability**: SYS-REQ-030
**Status**: Testing

---

**Story ID**: US-FE-007
**Title**: Session creation and switching
**Priority**: High
**Story Points**: 5

As a user
I want to create and switch chat sessions
So that context is preserved per session

**Acceptance Criteria**:
- [x] New session creation calls `/v1/sessions`
- [x] Session list shows recent sessions
- [x] Switching sessions changes conversation history
- [x] Sending a chat message with no active session creates one automatically

**Traceability**: SYS-REQ-032
**Status**: Complete

---

**Story ID**: US-FE-008
**Title**: API base URL configuration
**Priority**: Medium
**Story Points**: 3

As a user
I want to configure the API base URL
So that I can connect to a self-hosted backend

**Acceptance Criteria**:
- [x] Settings screen allows editing base URL
- [x] Requests use configured base URL
- [ ] Default base URL is `http://localhost:8080`
- [ ] Settings hint text reflects the default base URL

**Traceability**: SYS-REQ-031
**Status**: In Progress

---

**Story ID**: US-FE-009
**Title**: User provider API keys
**Priority**: Medium
**Story Points**: 5

As a user
I want to manage my own provider API keys
So that I can use my accounts for commercial models

**Acceptance Criteria**:
- [x] UI allows adding and removing provider keys
- [ ] Keys stored securely on device
- [ ] Requests to provider models use user keys

**Traceability**: SYS-REQ-035
**Status**: In Progress

---

**Story ID**: US-FE-010
**Title**: OSS access keys
**Priority**: Medium
**Story Points**: 5

As a user
I want to create and manage OSS access keys
So that I can access local models securely

**Acceptance Criteria**:
- [ ] UI allows creating and revoking OSS access keys
- [ ] Keys are stored and displayed securely

**Traceability**: SYS-REQ-036
**Status**: Not Started

---

**Story ID**: US-FE-011
**Title**: Invite-only registration and login/logout
**Priority**: High
**Story Points**: 5

As a user
I want to register only with an invite and log in/out
So that access is controlled

**Acceptance Criteria**:
- [x] Registration requires a valid invite token
- [x] Login returns a session/auth token
- [x] Logout clears local session and tokens
- [ ] Unauthenticated users are routed to Login before accessing any app pages
- [ ] Authenticated users land on Chat after app launch/login

**Traceability**: SYS-REQ-037
**Status**: In Progress

---

**Story ID**: US-FE-012
**Title**: User profile preferences
**Priority**: Medium
**Story Points**: 3

As a user
I want to save preferences like preferred models
So that the app opens in my preferred configuration

**Acceptance Criteria**:
- [ ] User can set preferred model(s)
- [ ] Preferences persist and apply on launch
- [ ] Preferences stored per user profile

**Traceability**: SYS-REQ-038
**Status**: Not Started

---

**Story ID**: US-FE-013
**Title**: User API tokens
**Priority**: Medium
**Story Points**: 3

As a user
I want to create and revoke private API tokens
So that I can call the API directly

**Acceptance Criteria**:
- [x] UI allows creating new API tokens
- [x] UI lists active tokens and supports revoke
- [x] Token values are shown once then masked

**Traceability**: SYS-REQ-039
**Status**: Complete

---

**Story ID**: US-FE-014
**Title**: UI layout auto-switch and lock
**Priority**: Medium
**Story Points**: 5

As a user
I want the UI to auto-switch by modality/device or lock a preferred layout
So that I can use the interface I like for each workflow

**Acceptance Criteria**:
- [ ] Auto mode switches to Chat layout for text models and Studio layout for image/3D
- [ ] Mobile devices default to Compact layout
- [ ] User can lock a preferred layout or manually switch
- [ ] Setting persists in user profile

**Traceability**: SYS-REQ-041
**Status**: Not Started

---

**Story ID**: US-FE-015
**Title**: Model download status display
**Priority**: Medium
**Story Points**: 3

As a user
I want to see download status badges on model cards
So that I know which models are ready, downloading, or failed

**Acceptance Criteria**:
- [x] Model cards show status badge: Ready (✓), Downloading (⌛), Failed (⚠)
- [ ] Downloading models show progress percentage if available
- [ ] Failed models show retry option
- [ ] Status updates without full page refresh

**Traceability**: SYS-REQ-043
**Status**: In Progress

---

**Story ID**: US-FE-016
**Title**: Model loading state indicator
**Priority**: High
**Story Points**: 3

As a user
I want to see if a model is loading, loaded, or busy
So that I know when I can expect a response

**Acceptance Criteria**:
- [x] Model cards show runtime status: Unloaded, Loading, Loaded, Busy
- [x] Loading shows spinner with optional progress
- [ ] Busy shows queue depth
- [ ] Status updates in real-time or near-real-time

**Traceability**: SYS-REQ-050
**Status**: In Progress

---

**Story ID**: US-FE-017
**Title**: Cancel in-flight request
**Priority**: High
**Story Points**: 3

As a user
I want to cancel a request while it's processing
So that I can stop long-running or unwanted generations

**Acceptance Criteria**:
- [x] Cancel button appears while request is in-flight
- [ ] Clicking cancel stops the request and shows confirmation
- [ ] Partial results shown if available
- [x] UI returns to ready state after cancel

**Traceability**: SYS-REQ-047
**Status**: In Progress

---

**Story ID**: US-FE-018
**Title**: Regenerate response button
**Priority**: Medium
**Story Points**: 2

As a user
I want to regenerate a response with same or modified parameters
So that I can get alternative outputs

**Acceptance Criteria**:
- [x] Regenerate button on each response
- [ ] Option to modify parameters before regenerating
- [x] New response replaces or shows alongside original

**Traceability**: SYS-REQ-048
**Status**: In Progress

---

**Story ID**: US-FE-019
**Title**: Queue position indicator
**Priority**: Medium
**Story Points**: 2

As a user
I want to see my position in the queue when waiting
So that I know how long to expect

**Acceptance Criteria**:
- [ ] Queue position shown when request is queued
- [ ] Position updates as queue moves
- [ ] Estimated wait time shown if available

**Traceability**: SYS-REQ-046
**Status**: Not Started

---

**Story ID**: US-FE-020
**Title**: Pre-load model button
**Priority**: Medium
**Story Points**: 2

As a user
I want to pre-load a model before using it
So that my first request is fast

**Acceptance Criteria**:
- [x] "Load" button on model cards that are unloaded
- [ ] Loading progress shown
- [x] Loaded status confirmed with checkmark

**Traceability**: SYS-REQ-049
**Status**: In Progress

---

**Story ID**: US-FE-021
**Title**: API endpoint alignment with backend
**Priority**: High
**Story Points**: 3

As a frontend developer
I want the SDK to call the exact backend endpoints and schemas
So that the UI can successfully communicate with the API

**Acceptance Criteria**:
- [x] Auth endpoints use `/v1/users/register` and `/v1/users/login`
- [x] Generation uses `/v1/generate` with `{model, modality, input, parameters?, stream?}`
- [x] Lifecycle endpoints include `model_id` in the path
- [x] Request status/cancel uses `/v1/requests/{request_id}`
- [x] User tokens and provider keys use `/v1/users/*` without `/me`

**Traceability**: SYS-REQ-055, SYS-REQ-056, SYS-REQ-057, SYS-REQ-058, SYS-REQ-059
**Status**: Complete

---

**Story ID**: US-FE-022
**Title**: Use shared Dart client package
**Priority**: High
**Story Points**: 3

As a frontend developer
I want the frontend to use the shared Dart client package from `clients/dart`
So that SDK logic is centralized and consistent with other consumers

**Acceptance Criteria**:
- [x] Frontend depends on the `pluggably_llm_client` package via path dependency
- [x] Frontend replaces `frontend/lib/sdk` usage with shared client imports
- [x] Existing API behavior remains unchanged
- [x] Frontend tests updated to use shared client models

**Traceability**: SYS-REQ-062
**Status**: Complete

---

**Story ID**: US-FE-023
**Title**: Add models via Hugging Face search
**Priority**: High
**Story Points**: 5

As a user
I want to search Hugging Face for models and download/register them
So that I can add new models from the UI

**Acceptance Criteria**:
- [ ] Add Model flow opens a search dialog/panel
- [ ] Search queries Hugging Face via the backend search endpoint
- [ ] Results show model name, modality, and provider/source
- [ ] Selecting a result triggers download/register via the API
- [ ] Search input filters large lists locally once results are loaded

**Traceability**: SYS-REQ-063
**Status**: Not Started

---

**Story ID**: US-FE-024
**Title**: Commercial provider credentials UI
**Priority**: High
**Story Points**: 5

As a user
I want to manage provider credentials with the right credential type
So that commercial models work with my accounts

**Acceptance Criteria**:
- [ ] Profile shows credential type per provider (API key, endpoint+key, OAuth token, service account JSON)
- [ ] Fields shown depend on provider requirements
- [ ] Save/validate calls backend credential endpoints

**Traceability**: SYS-REQ-064
**Status**: Not Started

---

**Story ID**: US-FE-025
**Title**: Left-pane sessions list
**Priority**: High
**Story Points**: 3

As a user
I want sessions listed in the left pane and to switch between them
So that I can manage conversation context without a dedicated sessions page

**Acceptance Criteria**:
- [ ] Sessions render under the left-pane Sessions menu item
- [ ] Selecting a session switches context
- [ ] List uses the documented sessions response shape

**Traceability**: SYS-REQ-065
**Status**: Not Started

---

**Story ID**: US-FE-026
**Title**: Session naming in UI
**Priority**: Medium
**Story Points**: 3

As a user
I want to name sessions and see names in the list
So that I can identify conversations quickly

**Acceptance Criteria**:
- [ ] Session create/update allows editing a title
- [ ] Left-pane list shows session titles (fallback to ID)

**Traceability**: SYS-REQ-066
**Status**: Not Started

---

**Story ID**: US-FE-027
**Title**: Message timestamps in UI
**Priority**: Medium
**Story Points**: 2

As a user
I want message timestamps shown in the chat history
So that I can see when prompts and responses occurred

**Acceptance Criteria**:
- [ ] Chat messages show a timestamp (relative or absolute)
- [ ] Session history uses timestamps from the API

**Traceability**: SYS-REQ-067
**Status**: Not Started

---

**Story ID**: US-FE-028
**Title**: Settings connection test
**Priority**: Medium
**Story Points**: 2

As a user
I want a Test Connection button in settings with a green check on success
So that I can verify the backend is reachable

**Acceptance Criteria**:
- [ ] Button calls health endpoint
- [ ] Success shows a green check icon
- [ ] Failure shows a clear error message

**Traceability**: SYS-REQ-068
**Status**: Not Started

---

**Story ID**: US-FE-029
**Title**: Image inputs for multimodal prompts
**Priority**: High
**Story Points**: 5

As a user
I want to attach images to my prompts (upload, paste, URL)
So that models that support image input can use them as context

**Acceptance Criteria**:
- [ ] User can attach images via file upload, clipboard paste, and URL
- [ ] Attached images are previewed and removable before sending
- [ ] Images are sent in `input.images` with the prompt
- [ ] Images are attached to the next prompt only (not global)
- [ ] Client-side resizing limits images to 1024px longest edge and a configurable total size limit
- [ ] Settings allow adjusting the total attachment size limit (default 10MB)
- [ ] Errors are shown for unsupported formats or blocked URL fetches

**Traceability**: SYS-REQ-070
**Status**: Not Started

---

## Traceability: System → Software

| System Req ID | Software Component | User Story ID(s) | Notes |
|---|---|---|---|
| SYS-REQ-025 | Frontend | US-FE-001 | UI availability |
| SYS-REQ-026 | Frontend | US-FE-001, US-FE-002 | Model selection |
| SYS-REQ-027 | Frontend | US-FE-003 | Dynamic parameters |
| SYS-REQ-028 | Frontend | US-FE-004 | Chat UI |
| SYS-REQ-029 | Frontend | US-FE-005 | Image UI |
| SYS-REQ-030 | Frontend | US-FE-006 | 3D UI |
| SYS-REQ-031 | Frontend | US-FE-008 | Separate hosting |
| SYS-REQ-032 | Frontend | US-FE-004, US-FE-007 | Sessions |
| SYS-REQ-035 | Frontend | US-FE-009 | User provider keys |
| SYS-REQ-036 | Frontend | US-FE-010 | OSS keys |
| SYS-REQ-037 | Frontend | US-FE-011 | Invite-only auth |
| SYS-REQ-038 | Frontend | US-FE-012 | User preferences |
| SYS-REQ-039 | Frontend | US-FE-013 | User API tokens |
| SYS-REQ-041 | Frontend | US-FE-014 | UI auto-switch/lock |
| SYS-REQ-043 | Frontend | US-FE-015 | Model download status |
| SYS-REQ-046 | Frontend | US-FE-019 | Queue position |
| SYS-REQ-047 | Frontend | US-FE-017 | Request cancellation |
| SYS-REQ-048 | Frontend | US-FE-018 | Regenerate |
| SYS-REQ-049 | Frontend | US-FE-020 | Pre-load model |
| SYS-REQ-050 | Frontend | US-FE-016 | Model loading state |
| SYS-REQ-055 | Frontend | US-FE-021 | Auth endpoint alignment |
| SYS-REQ-056 | Frontend | US-FE-021 | Generate endpoint alignment |
| SYS-REQ-057 | Frontend | US-FE-021 | Lifecycle endpoint alignment |
| SYS-REQ-058 | Frontend | US-FE-021 | Request endpoint alignment |
| SYS-REQ-059 | Frontend | US-FE-021 | User resource endpoint alignment |
| SYS-REQ-062 | Frontend | US-FE-022 | Shared Dart client usage |
| SYS-REQ-063 | Frontend | US-FE-023 | Add model flow |
| SYS-REQ-064 | Frontend | US-FE-024 | Provider credentials UI |
| SYS-REQ-065 | Frontend | US-FE-025 | Left-pane sessions list |
| SYS-REQ-066 | Frontend | US-FE-026 | Session naming |
| SYS-REQ-067 | Frontend | US-FE-027 | Message timestamps |
| SYS-REQ-068 | Frontend | US-FE-028 | Connection test |
| SYS-REQ-070 | Frontend | US-FE-029 | Image input attachments |

## Definition of Done
- User stories and acceptance criteria defined
- Traceability matrix updated
- Dependencies identified
