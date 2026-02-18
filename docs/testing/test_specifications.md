# Test Specifications

**Project**: Pluggably LLM API Gateway
**Date**: January 26, 2026
**Status**: Updated (Pending Approval)

## Test Strategy
- Prioritize automated unit and integration tests.
- Use system tests for end-to-end API flows.
- Manual tests only when automation is not feasible (e.g., large model downloads or GPU-only flows).

## System Test Specifications

**TEST-SYS-001**: Standard multimodal API request/response
- **Purpose**: Verify standardized requests for text/image/3D
- **Preconditions**: Service running, at least one model available
- **Steps**:
  1. Send a text generation request
  2. Send an image generation request
  3. Send a 3D generation request
- **Expected**:
  - Responses follow standard schema
  - Correct modality output populated
- **Traceability**: SYS-REQ-001, SYS-REQ-004

**TEST-SYS-002**: Model catalog endpoint
- **Purpose**: Verify available models endpoint
- **Steps**:
  1. Call model catalog endpoint
  2. Filter by modality
- **Expected**:
  - Returns model list with capabilities
  - Filter works
- **Traceability**: SYS-REQ-015, DATA-REQ-006

**TEST-SYS-003**: Model download job workflow
- **Purpose**: Verify async download and status
- **Steps**:
  1. Submit model download
  2. Poll job status
- **Expected**:
  - Status updates from queued → running → completed
- **Traceability**: SYS-REQ-010, SYS-REQ-013

**TEST-SYS-010**: Local model auto-discovery
- **Purpose**: Verify locally installed models are discovered and listed
- **Preconditions**: At least one `.gguf` file present under model storage path
- **Steps**:
  1. Start the service
  2. Call model catalog endpoint
- **Expected**:
  - Discovered model appears with size, local path, and status
- **Traceability**: SYS-REQ-018, DATA-REQ-005, DATA-REQ-006

**TEST-SYS-011**: Parameter schema endpoint
- **Purpose**: Verify schema endpoint returns parameter documentation
- **Steps**:
  1. Call schema endpoint
  2. Inspect parameters section
- **Expected**:
  - Parameter docs include temperature, max_tokens, format, stream
  - Model selection guidance is present
- **Traceability**: SYS-REQ-019, INT-REQ-005, DATA-REQ-007

**TEST-SYS-012**: Session creation and reuse
- **Purpose**: Verify session creation and multi-turn requests
- **Steps**:
  1. Create a session
  2. Send a text request with session_id
  3. Send a follow-up request with same session_id
- **Expected**:
  - Session ID is returned and accepted
  - Session context is reused
- **Traceability**: SYS-REQ-020, DATA-REQ-008

**TEST-SYS-013**: Session lifecycle management
- **Purpose**: Verify list/reset/close session APIs
- **Steps**:
  1. List sessions
  2. Reset a session
  3. Close a session
- **Expected**:
  - Session list shows metadata
  - Reset clears context
  - Closed sessions are marked inactive
- **Traceability**: SYS-REQ-021, INT-REQ-006

**TEST-SYS-014**: Session state token passthrough
- **Purpose**: Verify client-supplied state tokens are accepted and returned
- **Steps**:
  1. Create a session
  2. Send a generate request with `state_tokens`
  3. Send a follow-up request without tokens
- **Expected**:
  - Response includes updated state tokens
  - Session preserves tokens when omitted on subsequent calls
- **Traceability**: SYS-REQ-022, DATA-REQ-009

**TEST-SYS-CR003-001**: Auto selection when model omitted
- **Purpose**: Verify the router resolves a model when `model` is omitted or set to `auto`
- **Steps**:
  1. Send a generate request without `model`
  2. Repeat with `model: "auto"`
- **Expected**:
  - Response includes resolved `model`
  - Output is generated successfully
- **Traceability**: SYS-REQ-CR003-001

**TEST-SYS-CR003-002**: Auto selection with image input
- **Purpose**: Verify image inputs route to an image-capable model under Auto
- **Steps**:
  1. Send a request with `input.images` and `model: "auto"`
- **Expected**:
  - Selected model is the default image model (or first available image model)
- **Traceability**: SYS-REQ-CR003-002

**TEST-SYS-CR003-003**: Manual model selection preserved
- **Purpose**: Verify explicit model IDs bypass auto-selection
- **Steps**:
  1. Send a request with an explicit `model` ID
- **Expected**:
  - Router uses the requested model
- **Traceability**: SYS-REQ-CR003-004

**TEST-UNIT-006**: Client library request/response models
- **Purpose**: Verify SDK request/response serialization matches API schema (Python and Dart/Flutter)
- **Steps**:
  1. Construct SDK request in Python and Dart/Flutter
  2. Serialize to JSON
  3. Compare against OpenAPI schema expectations
- **Expected**:
  - Fields and types match API contract in both clients
- **Traceability**: SYS-REQ-023, DATA-REQ-010

**TEST-UNIT-007**: Client session helpers
- **Purpose**: Verify SDK session helper methods call correct endpoints in both clients
- **Steps**:
  1. Invoke create/reset/close helpers
  2. Inspect constructed URLs and payloads
- **Expected**:
  - Endpoints and payloads match contract
- **Traceability**: SYS-REQ-024, INT-REQ-008

## System Test Specifications (MVP Additions)

**TEST-SYS-MVP-001**: Sessions list contract
- **Purpose**: Verify session list returns a consistent JSON shape
- **Steps**:
  1. Call `GET /v1/sessions`
- **Expected**:
  - Response is `{ "sessions": [...] }`
  - Each session includes id, title, created_at, last_used_at
- **Traceability**: SYS-REQ-065

**TEST-SYS-MVP-002**: Session naming
- **Purpose**: Verify session title is persisted and returned
- **Steps**:
  1. Create a session with a title
  2. Update the session title
  3. Fetch session list and details
- **Expected**:
  - Title is returned in create/update/get/list
- **Traceability**: SYS-REQ-066

**TEST-SYS-MVP-003**: Message timestamps
- **Purpose**: Verify session messages include timestamps
- **Steps**:
  1. Create a session
  2. Send a prompt and receive a response
  3. Fetch session history
- **Expected**:
  - Messages include `created_at` timestamps (ISO 8601)
- **Traceability**: SYS-REQ-067

**TEST-SYS-MVP-004**: Hugging Face search endpoint
- **Purpose**: Verify Hugging Face search endpoint behavior
- **Steps**:
  1. Call `GET /v1/models/search?source=huggingface&query=llama`
- **Expected**:
  - Response includes model id, name, tags, modality hints
  - Pagination fields present when applicable
- **Traceability**: SYS-REQ-063

## Test Reporting
Automated test runs should generate reports for review.

- Backend: JUnit XML report from pytest
- Frontend: Flutter machine report

Use the script documented in [docs/ops/test_reporting.md](docs/ops/test_reporting.md).

**TEST-INT-CR001-001**: Auth endpoint alignment
- **Purpose**: Verify frontend SDK uses `/v1/users/*` auth endpoints
- **Steps**:
  1. Call `register()` in frontend SDK with mock client
  2. Call `login()` in frontend SDK with mock client
- **Expected**:
  - Requests hit `/v1/users/register` and `/v1/users/login`
- **Traceability**: SYS-REQ-055

**TEST-INT-CR001-002**: Generate endpoint alignment
- **Purpose**: Verify frontend SDK uses `/v1/generate` with correct schema
- **Steps**:
  1. Call `generate()` in frontend SDK with mock client
- **Expected**:
  - Request hits `/v1/generate`
  - Body includes `model`, `modality`, `input`, `parameters`
- **Traceability**: SYS-REQ-056

**TEST-INT-CR001-003**: Lifecycle endpoint alignment
- **Purpose**: Verify lifecycle endpoints include `model_id` in path
- **Steps**:
  1. Call `getModelStatus()` in frontend SDK with mock client
  2. Call `loadModel()` in frontend SDK with mock client
  3. Call `unloadModel()` in frontend SDK with mock client
- **Expected**:
  - Requests hit `/v1/models/{model_id}/status|load|unload`
- **Traceability**: SYS-REQ-057

**TEST-INT-CR001-004**: Request endpoint alignment
- **Purpose**: Verify request endpoints use plural `/v1/requests/*`
- **Steps**:
  1. Call `getRequestStatus()` in frontend SDK with mock client
  2. Call `cancelRequest()` in frontend SDK with mock client
- **Expected**:
  - Requests hit `/v1/requests/{request_id}/status|cancel`
- **Traceability**: SYS-REQ-058

**TEST-INT-CR001-005**: User resource endpoint alignment
- **Purpose**: Verify user tokens and provider keys use `/v1/users/*` without `/me`
- **Steps**:
  1. Call `listUserTokens()` in frontend SDK with mock client
  2. Call `listProviderKeys()` in frontend SDK with mock client
- **Expected**:
  - Requests hit `/v1/users/tokens` and `/v1/users/provider-keys`
- **Traceability**: SYS-REQ-059

**TEST-INT-CR001-006**: Session update endpoint
- **Purpose**: Verify backend provides PUT `/v1/sessions/{session_id}`
- **Steps**:
  1. Call update session endpoint
- **Expected**:
  - Returns updated session object
- **Traceability**: SYS-REQ-060

**TEST-INT-001**: Provider adapter error mapping
- **Purpose**: Ensure provider errors map to standard error codes
- **Steps**:
  1. Simulate provider error
- **Expected**:
  - Standard error response returned
- **Traceability**: SYS-REQ-002, SYS-NFR-002

**TEST-INT-002**: Registry ↔ Storage interaction
- **Purpose**: Validate registry updates on storage changes
- **Steps**:
  1. Trigger storage cleanup
- **Expected**:
  - Registry updated for evicted models
- **Traceability**: SYS-REQ-012

**TEST-INT-003**: Python client end-to-end flow
- **Purpose**: Verify Python client exercises core endpoints against a running server
- **Preconditions**: Server running locally; API key configured
- **Steps**:
  1. Create a session using Python client
  2. Generate text in-session
  3. List models and providers
  4. Close the session
- **Expected**:
  - All calls succeed with typed responses
  - Session lifecycle endpoints behave correctly
- **Traceability**: SYS-REQ-023, SYS-REQ-024

**TEST-INT-004**: Dart/Flutter client end-to-end flow
- **Purpose**: Verify Dart/Flutter client exercises core endpoints against a running server
- **Preconditions**: Server running locally; API key configured; Dart SDK installed
- **Steps**:
  1. Create a session using Dart client
  2. Generate text in-session
  3. List models and providers
  4. Close the session
- **Expected**:
  - All calls succeed with typed responses
  - Session lifecycle endpoints behave correctly
- **Traceability**: SYS-REQ-023, SYS-REQ-024

## Manual Test Specifications

**TEST-MAN-MVP-001**: Add model via Hugging Face search
- **Purpose**: Verify add-model UI flow and download initiation
- **Preconditions**: Frontend running; backend running; Hugging Face reachable
- **Steps**:
  1. Open Add Model flow
  2. Search for a model
  3. Select a model and start download
- **Expected**:
  - Results display
  - Download starts and status is shown
- **Traceability**: SYS-REQ-063

**TEST-MAN-MVP-002**: Provider credential types
- **Purpose**: Verify provider credential UI supports multiple credential types
- **Preconditions**: Authenticated user
- **Steps**:
  1. Open profile credentials section
  2. Select provider with API key
  3. Select provider requiring endpoint+key or OAuth token
  4. Save credentials
- **Expected**:
  - Fields match provider requirements
  - Save succeeds and persists
- **Traceability**: SYS-REQ-064

**TEST-MAN-MVP-003**: Left-pane sessions list
- **Purpose**: Verify session list appears under left pane and switches context
- **Preconditions**: Frontend running; sessions available
- **Steps**:
  1. Open the left-pane Sessions section
  2. Select a session
  3. Verify chat history updates
- **Expected**:
  - Sessions display and switching works
- **Traceability**: SYS-REQ-065, SYS-REQ-066

**TEST-MAN-MVP-004**: Message timestamps
- **Purpose**: Verify timestamps shown for prompts/responses
- **Preconditions**: Session with messages
- **Steps**:
  1. Send a prompt
  2. Observe timestamps on messages
- **Expected**:
  - Timestamps rendered and consistent
- **Traceability**: SYS-REQ-067

**TEST-MAN-MVP-005**: Settings connection test
- **Purpose**: Verify health check button shows green check on success
- **Preconditions**: Backend reachable at configured base URL
- **Steps**:
  1. Click Test Connection
- **Expected**:
  - Green check on success, error message on failure
- **Traceability**: SYS-REQ-068

**TEST-MAN-018**: Image inputs in chat
- **Purpose**: Validate image upload, paste, and URL attachments
- **Preconditions**: Frontend running; model that supports image input
- **Steps**:
  1. Attach an image via upload/paste/URL
  2. Send a prompt
  3. Verify image is sent and rendered in the user message
- **Expected**:
  - Images are attached and sent with the prompt
  - Errors shown for invalid formats or blocked URLs
- **Traceability**: SYS-REQ-070

**TEST-MAN-CR001-001**: API endpoint reference review
- **Purpose**: Verify API endpoint reference is complete and accurate
- **Steps**:
  1. Open `docs/api_endpoints.md`
  2. Confirm endpoints and schemas match backend implementation
- **Expected**:
  - All documented endpoints exist and are accurate
- **Traceability**: SYS-REQ-061

**TEST-MAN-CR002-001**: Shared Dart client usage
- **Purpose**: Verify frontend uses the shared Dart client package
- **Steps**:
  1. Open frontend `pubspec.yaml` and confirm path dependency on `../clients/dart`
  2. Search frontend codebase for imports from `pluggably_llm_client`
  3. Confirm `frontend/lib/sdk` is no longer referenced
- **Expected**:
  - Frontend depends on shared package and uses its models/client
  - No local SDK usage remains
- **Traceability**: SYS-REQ-062

**TEST-MAN-004**: Frontend model selection and dynamic parameters
- **Purpose**: Verify model selection and schema-driven parameter panel in the frontend
- **Preconditions**: Frontend running; backend running; API key configured
- **Steps**:
  1. Open the frontend and select a text model
  2. Open the settings pane and confirm parameter inputs render from schema
  3. Switch to an image model and confirm parameters update dynamically
- **Expected**:
  - Model list and modality filtering work
  - Parameter panel updates with the selected model schema
- **Traceability**: SYS-REQ-025, SYS-REQ-026, SYS-REQ-027

**TEST-MAN-005**: Text chat UI streaming
- **Purpose**: Verify chat-like UI renders streaming responses
- **Preconditions**: Frontend running; backend running with streaming enabled
- **Steps**:
  1. Select a text model
  2. Send a prompt in the chat UI
  3. Observe streaming response in the chat bubble
- **Expected**:
  - Response appears incrementally in the UI
- **Traceability**: SYS-REQ-028

**TEST-MAN-006**: Image generation UI
- **Purpose**: Verify image generation UI supports gallery and downloads
- **Preconditions**: Frontend running; backend running with image model available
- **Steps**:
  1. Select an image model and enter a prompt
  2. Generate images and observe the gallery
  3. Download an image
- **Expected**:
  - Images display in a gallery
  - Download succeeds
- **Traceability**: SYS-REQ-029

**TEST-MAN-007**: 3D generation UI
- **Purpose**: Verify 3D UI supports preview and download
- **Preconditions**: Frontend running; backend running with 3D model available
- **Steps**:
  1. Select a 3D model and enter a prompt
  2. Generate and view the 3D preview
  3. Download the 3D asset
- **Expected**:
  - 3D viewer renders and supports interaction
  - Download succeeds
- **Traceability**: SYS-REQ-030

**TEST-MAN-008**: Separate hosting configuration
- **Purpose**: Verify web frontend can point to a separately hosted backend
- **Preconditions**: Frontend hosted separately; backend reachable
- **Steps**:
  1. Configure API base URL in frontend settings
  2. Verify requests go to the configured backend
- **Expected**:
  - Frontend successfully communicates with the configured backend
- **Traceability**: SYS-REQ-031

**TEST-INT-005**: Model registry persistence
- **Purpose**: Verify model registry persists internal/external models across restarts
- **Preconditions**: Registry storage configured
- **Steps**:
  1. Register or discover a model
  2. Restart the service
  3. Query model list
- **Expected**:
  - Model remains present with same metadata and parameters
- **Traceability**: SYS-REQ-033

**TEST-INT-006**: Schema registry synchronization
- **Purpose**: Verify `/v1/schema` reflects stored model parameter schemas
- **Preconditions**: Model registry contains schema definitions
- **Steps**:
  1. Query `/v1/schema` for a model
  2. Compare to stored schema in registry
- **Expected**:
  - Schema matches registry definition
- **Traceability**: SYS-REQ-034

**TEST-INT-007**: Model documentation enrichment
- **Purpose**: Verify model registry pulls docs and parameter guidance from Hugging Face
- **Preconditions**: HF metadata endpoint reachable; model has a model card
- **Steps**:
  1. Register a Hugging Face model
  2. Fetch model entry from registry
- **Expected**:
  - Model entry includes description/usage docs and parameter guidance if available
  - Registration still succeeds if HF data is missing
- **Traceability**: SYS-REQ-040

**TEST-INT-008**: Async model downloads
- **Purpose**: Verify model downloads run in background without blocking API
- **Preconditions**: Download worker enabled
- **Steps**:
  1. Trigger a model download
  2. Immediately call a standard API endpoint
- **Expected**:
  - API responds without waiting for download completion
  - Download job continues in background
- **Traceability**: SYS-REQ-042

**TEST-INT-009**: Model status reporting
- **Purpose**: Verify model list exposes download status
- **Preconditions**: Active download in progress
- **Steps**:
  1. Trigger a model download
  2. Call model list endpoint
- **Expected**:
  - Model status shows downloading then ready/failed
- **Traceability**: SYS-REQ-043

**TEST-INT-010**: Download deduplication
- **Purpose**: Prevent duplicate downloads for the same model
- **Preconditions**: Model download in progress or completed
- **Steps**:
  1. Trigger download for a model
  2. Trigger the same download again
- **Expected**:
  - System reuses existing download or returns existing model entry
- **Traceability**: SYS-REQ-044

**TEST-INT-011**: Model lifecycle management
- **Purpose**: Verify model loading, idle timeout, and eviction
- **Preconditions**: Multiple models available; lifecycle config set
- **Steps**:
  1. Load a model
  2. Wait for idle timeout
  3. Verify model unloads
  4. Load multiple models to trigger LRU eviction
- **Expected**:
  - Model unloads after idle timeout
  - LRU eviction works when limit reached
  - Pinned models never unload
- **Traceability**: SYS-REQ-045

**TEST-INT-012**: Request queueing
- **Purpose**: Verify requests queue when resources are busy
- **Preconditions**: Local model loaded; concurrent request limit = 1
- **Steps**:
  1. Send a long-running request
  2. Immediately send a second request
- **Expected**:
  - Second request queues
  - Queue position returned
  - Second request completes after first
- **Traceability**: SYS-REQ-046

**TEST-INT-013**: Prepare/load model endpoint
- **Purpose**: Verify model pre-loading
- **Preconditions**: Model available but unloaded
- **Steps**:
  1. Call POST /v1/models/{id}/load
  2. Poll model runtime status
- **Expected**:
  - Status transitions: unloaded → loading → loaded
  - Subsequent requests are fast
- **Traceability**: SYS-REQ-049

**TEST-INT-014**: Model runtime status
- **Purpose**: Verify runtime status in model queries
- **Preconditions**: Model available
- **Steps**:
  1. Query model when unloaded
  2. Load model and query during loading
  3. Query when loaded
  4. Query while busy processing
- **Expected**:
  - Status reflects: unloaded, loading, loaded, busy
- **Traceability**: SYS-REQ-050

**TEST-INT-015**: Get loaded models endpoint
- **Purpose**: Verify listing of loaded models
- **Preconditions**: At least one model loaded
- **Steps**:
  1. Load a model
  2. Call GET /v1/models/loaded
- **Expected**:
  - Returns list of loaded models with memory usage
- **Traceability**: SYS-REQ-051

**TEST-INT-016**: Default pinned model
- **Purpose**: Verify default model is always loaded
- **Preconditions**: Default model configured
- **Steps**:
  1. Start service
  2. Check default model status immediately
  3. Wait for idle timeout
  4. Check status again
- **Expected**:
  - Default model is loaded on startup
  - Default model remains loaded after idle timeout
- **Traceability**: SYS-REQ-052

**TEST-INT-017**: Fallback model configuration
- **Purpose**: Verify fallback chain works
- **Preconditions**: Fallback chain configured
- **Steps**:
  1. Request with primary model unavailable
  2. Verify fallback model serves request
- **Expected**:
  - Fallback model used
  - Response indicates which model served
- **Traceability**: SYS-REQ-053

**TEST-SYS-015**: Request queueing end-to-end
- **Purpose**: Verify queue position feedback to clients
- **Preconditions**: Server running with queue enabled
- **Steps**:
  1. Send multiple concurrent requests
  2. Observe queue position updates
- **Expected**:
  - Queue positions decrease as requests complete
- **Traceability**: SYS-REQ-046

**TEST-SYS-016**: Request cancellation end-to-end
- **Purpose**: Verify request cancellation
- **Preconditions**: Server running with cancellation enabled
- **Steps**:
  1. Send a long-running request
  2. Call cancel endpoint
  3. Verify cancellation
- **Expected**:
  - Request is cancelled
  - Resources freed
  - Appropriate response returned
- **Traceability**: SYS-REQ-047

**TEST-SYS-017**: Session survives model spindown
- **Purpose**: Verify session state persists and is resumable after model is unloaded/spun down and reloaded
- **Preconditions**: Server running with model lifecycle management enabled
- **Steps**:
  1. Create a session and send several chat messages
  2. Wait for model idle timeout or trigger model unload
  3. Send a new message using the same session
  4. Observe model reload and session resumption
- **Expected**:
  - Session context/history is preserved after model spindown
  - Model reloads transparently on next request
  - Session continues with full context
- **Traceability**: SYS-REQ-054

**TEST-MAN-012**: Invite-only registration and authentication
- **Purpose**: Verify invite-only user registration and login/logout
- **Preconditions**: Backend running with invite requirement enabled
- **Steps**:
  1. Attempt registration without invite token
  2. Register with a valid invite token
  3. Log in and log out
- **Expected**:
  - Registration without invite is rejected
  - Registration with invite succeeds
  - Login/logout work and session/auth token is issued/cleared
- **Traceability**: SYS-REQ-037

**TEST-MAN-013**: User profile preferences
- **Purpose**: Verify user profile preferences persist and apply
- **Preconditions**: Authenticated user
- **Steps**:
  1. Set preferred model and UI defaults
  2. Restart app or refresh session
  3. Confirm preferences persist and apply
- **Expected**:
  - Preferences are saved and restored
  - Preferred model is selected by default
- **Traceability**: SYS-REQ-038

**TEST-MAN-014**: User API tokens
- **Purpose**: Verify user-created API tokens for LLM API access
- **Preconditions**: Authenticated user
- **Steps**:
  1. Create a new API token
  2. Use the token to call the API
  3. Revoke the token and retry
- **Expected**:
  - Token grants access while active
  - Revoked token is rejected
- **Traceability**: SYS-REQ-039

**TEST-MAN-015**: UI layout auto-switch and lock
- **Purpose**: Verify layout switching by modality/device and user override
- **Preconditions**: Frontend running; user profile available
- **Steps**:
  1. Enable auto mode and select a text model
  2. Switch to an image/3D model
  3. Test on mobile viewport
  4. Lock a layout and verify no auto-switching
- **Expected**:
  - Text models use Chat layout
  - Image/3D use Studio layout
  - Mobile uses Compact layout
  - Locked/manual modes override auto switching
- **Traceability**: SYS-REQ-041

## Unit Test Specifications

**TEST-UNIT-001**: Request validation
- **Purpose**: Validate request schema enforcement
- **Steps**:
  1. Submit invalid payload
- **Expected**:
  - Validation error with field details
- **Traceability**: SYS-REQ-001

**TEST-UNIT-002**: Model selection logic
- **Purpose**: Verify routing decision based on model selector
- **Traceability**: SYS-REQ-011

**TEST-UNIT-003**: Auth middleware
- **Purpose**: Verify API key and JWT auth handling
- **Traceability**: SYS-REQ-014

**TEST-UNIT-004**: Storage policy enforcement
- **Purpose**: Ensure disk usage bounds respected
- **Traceability**: SYS-REQ-012, SYS-NFR-007

**TEST-UNIT-005**: Config loading
- **Purpose**: Verify config from env vars and file is loaded correctly
- **Traceability**: SYS-REQ-006

**TEST-SYS-004**: Health and readiness endpoints
- **Purpose**: Verify health/readiness endpoints respond correctly
- **Steps**:
  1. Call /health
  2. Call /ready
- **Expected**:
  - /health returns 200 with status
  - /ready returns 200 when ready, 503 when not
- **Traceability**: SYS-REQ-007

**TEST-SYS-005**: Observability metrics endpoint
- **Purpose**: Verify metrics are exposed
- **Steps**:
  1. Make requests to API
  2. Verify metrics endpoint shows counts
- **Expected**:
  - Metrics include request count, errors, latency
- **Traceability**: SYS-REQ-008

**TEST-SYS-006**: Artifact store output
- **Purpose**: Verify large outputs return artifact URLs
- **Steps**:
  1. Request image/3D generation exceeding inline threshold
- **Expected**:
  - Response includes artifact URL
  - URL is downloadable and expires
- **Traceability**: SYS-REQ-016

**TEST-SYS-007**: Streaming text response
- **Purpose**: Verify SSE streaming for text generation
- **Steps**:
  1. Request text generation with stream=true
- **Expected**:
  - Response is SSE stream
  - Tokens arrive incrementally
- **Traceability**: SYS-REQ-017

## Traceability
Requirements → Verification

| Requirement ID | Verification Type | Test/Procedure ID | Location | Notes |
|---|---|---|---|---|
| SYS-REQ-001 | Automated | TEST-SYS-001, TEST-UNIT-001 | tests/system/, tests/unit/ | |
| SYS-REQ-002 | Automated | TEST-INT-001 | tests/integration/ | |
| SYS-REQ-003 | Automated | TEST-SYS-001 | tests/system/ | |
| SYS-REQ-004 | Automated | TEST-SYS-001 | tests/system/ | |
| SYS-REQ-006 | Automated | TEST-UNIT-005 | tests/unit/ | |
| SYS-REQ-007 | Automated | TEST-SYS-004 | tests/system/ | |
| SYS-REQ-008 | Automated | TEST-SYS-005 | tests/system/ | |
| SYS-REQ-010 | Automated | TEST-SYS-003 | tests/system/ | |
| SYS-REQ-011 | Automated | TEST-UNIT-002 | tests/unit/ | |
| SYS-REQ-012 | Automated | TEST-INT-002, TEST-UNIT-004 | tests/integration/, tests/unit/ | |
| SYS-REQ-013 | Automated | TEST-SYS-003 | tests/system/ | |
| SYS-REQ-014 | Automated | TEST-UNIT-003 | tests/unit/ | |
| SYS-REQ-015 | Automated | TEST-SYS-002 | tests/system/ | |
| SYS-REQ-016 | Automated | TEST-SYS-006 | tests/system/ | |
| SYS-REQ-017 | Automated | TEST-SYS-007 | tests/system/ | |
| SYS-REQ-018 | Automated | TEST-SYS-010 | tests/system/ | |
| SYS-REQ-019 | Automated | TEST-SYS-011 | tests/system/ | |
| SYS-REQ-020 | Automated | TEST-SYS-012 | tests/system/ | |
| SYS-REQ-021 | Automated | TEST-SYS-013 | tests/system/ | |
| SYS-REQ-022 | Automated | TEST-SYS-014 | tests/system/ | |
| SYS-REQ-023 | Automated | TEST-UNIT-006, TEST-INT-003, TEST-INT-004 | tests/client/unit/, tests/client/integration/ | |
| SYS-REQ-024 | Automated | TEST-UNIT-007, TEST-INT-003, TEST-INT-004 | tests/client/unit/, tests/client/integration/ | |
| SYS-REQ-025 | Manual | TEST-MAN-004 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-026 | Manual | TEST-MAN-004 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-027 | Manual | TEST-MAN-004 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-028 | Manual | TEST-MAN-005 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-029 | Manual | TEST-MAN-006 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-030 | Manual | TEST-MAN-007 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-031 | Manual | TEST-MAN-008 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-032 | Manual | TEST-MAN-009 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-033 | Automated | TEST-INT-005 | tests/integration/ | |
| SYS-REQ-034 | Automated | TEST-INT-006 | tests/integration/ | |
| SYS-REQ-035 | Manual | TEST-MAN-010 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-036 | Manual | TEST-MAN-011 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-037 | Manual | TEST-MAN-012 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-038 | Manual | TEST-MAN-013 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-039 | Manual | TEST-MAN-014 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-040 | Automated | TEST-INT-007 | tests/integration/ | |
| SYS-REQ-041 | Manual | TEST-MAN-015 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-042 | Automated | TEST-INT-008 | tests/integration/ | |
| SYS-REQ-043 | Automated | TEST-INT-009 | tests/integration/ | |
| SYS-REQ-044 | Automated | TEST-INT-010 | tests/integration/ | |
| SYS-REQ-045 | Automated | TEST-INT-011 | tests/integration/ | Model lifecycle |
| SYS-REQ-046 | Automated | TEST-INT-012, TEST-SYS-015 | tests/integration/, tests/system/ | Request queueing |
| SYS-REQ-047 | Automated | TEST-SYS-016 | tests/system/ | Request cancellation |
| SYS-REQ-048 | Manual | TEST-MAN-017 | docs/testing/manual_test_procedures.md | Regenerate |
| SYS-REQ-049 | Automated | TEST-INT-013 | tests/integration/ | Prepare/load model |
| SYS-REQ-050 | Automated | TEST-INT-014 | tests/integration/ | Model runtime status |
| SYS-REQ-051 | Automated | TEST-INT-015 | tests/integration/ | Get loaded models |
| SYS-REQ-052 | Automated | TEST-INT-016 | tests/integration/ | Default pinned model |
| SYS-REQ-053 | Automated | TEST-INT-017 | tests/integration/ | Fallback configuration |
| SYS-REQ-054 | Automated | TEST-SYS-017 | tests/system/ | Session survives model spindown |

## Definition of Ready / Done
**Ready**
- Test cases defined for all key requirements.
- Traceability matrix filled.

**Done**
- Tests implemented and passing.
- Manual test procedures created where needed.
