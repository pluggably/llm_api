# Manual Test Procedures

**Project**: Pluggably LLM API Gateway
**Date**: January 26, 2026
**Status**: Updated (Pending Approval)

## TEST-MAN-001: Large model download on constrained host
**Purpose**: Validate long-running download behavior and disk usage handling
**Automation**: Covered by automated system tests `TEST-SYS-003` in [tests/system/test_model_download_workflow.py](tests/system/test_model_download_workflow.py).
Manual run only if validating real storage constraints in a live environment.
**Preconditions**: Server running; limited disk quota configured
**Steps**:
1. Start the backend with storage limits configured (set max storage and retention in config).
2. Open the API client (curl/Postman) and call `POST /v1/models/download` with a multi-GB model.
3. Record the returned job ID.
4. Poll `GET /v1/jobs/{job_id}` every 10–15 seconds.
5. If the download completes, confirm status = completed and progress = 100.
6. If the storage limit is exceeded, confirm status = failed and error includes storage limit details.
**Expected Results**:
- Status updates show progress
- If storage limit is exceeded, download fails gracefully with a clear error
- Registry reflects final status

## TEST-MAN-002: GPU-only model execution
**Purpose**: Validate local runner on GPU-only model
**Preconditions**: Host with GPU, compatible drivers, model available
**Steps**:
1. Verify GPU drivers are installed and visible to the backend.
2. Download a GPU-only model via `POST /v1/models/download`.
3. Wait for job completion.
4. Send a generation request using the GPU-only model ID.
5. Inspect logs to confirm GPU backend usage.
**Expected Results**:
- Response generated successfully
- Logs include hardware backend info

## TEST-MAN-003: Artifact download via URL
**Purpose**: Validate artifact URL response flow
**Automation**: Covered by automated system tests `TEST-SYS-006` in [tests/system/test_artifact_store.py](tests/system/test_artifact_store.py).
Manual run only if validating real artifact storage backends.
**Preconditions**: Artifact store enabled
**Steps**:
1. Set artifact inline threshold low (or choose a large output model) to force artifact storage.
2. Send an image/3D generation request that exceeds the threshold.
3. Confirm the response contains artifact URLs with expiration timestamps.
4. Open the artifact URL in a browser or download with curl.
5. Verify the download succeeds and content matches expected format.
**Expected Results**:
- URL is valid and downloadable
- URL expires after configured TTL

## TEST-MAN-004: Frontend model selection and dynamic parameters
**Purpose**: Validate model selection and schema-driven parameter panel
**Preconditions**: Frontend running; backend running; API key configured
**Steps**:
1. Launch the frontend and log in if required.
2. Navigate to Models.
3. Select a text model.
4. Open the settings pane/drawer.
5. Verify inputs match `/v1/schema` (types, defaults, labels).
6. Switch to an image model and reopen settings.
7. Confirm parameters update to image-specific settings.
**Expected Results**:
- Model list and modality filtering work
- Parameter panel updates with the selected model schema

## TEST-MAN-005: Text chat UI streaming
**Purpose**: Validate streaming responses in the chat UI
**Preconditions**: Frontend running; backend streaming enabled
**Steps**:
1. Select a text model.
2. Enter a prompt in the chat input.
3. Click Send.
4. Confirm the assistant bubble shows streaming updates (token-by-token).
5. Confirm the final response finishes and the “Thinking…” indicator disappears.
**Expected Results**:
- Response appears incrementally in the UI

## TEST-MAN-006: Image generation UI
**Purpose**: Validate image generation gallery and download
**Preconditions**: Frontend running; image model available
**Steps**:
1. Select an image model in the Models list.
2. Enter a prompt and submit generation.
3. Wait for images to appear in the gallery grid.
4. Click an image to preview.
5. Use the download action and confirm the file saves locally.
6. Verify the downloaded file opens and matches the preview.
**Expected Results**:
- Images display in a gallery
- Download succeeds

## TEST-MAN-007: 3D generation UI
**Purpose**: Validate 3D preview and download
**Preconditions**: Frontend running; 3D model available
**Steps**:
1. Select a 3D model in the Models list.
2. Enter a prompt and submit generation.
3. Wait for the 3D preview to load.
4. Rotate/zoom the model to confirm interactivity.
5. Download the asset and confirm file integrity.
6. Open the OBJ in a local viewer to confirm geometry loads.
**Expected Results**:
- 3D viewer renders and supports interaction
- Download succeeds

## TEST-MAN-008: Separate hosting configuration
**Purpose**: Validate frontend API base URL configuration
**Preconditions**: Frontend hosted separately; backend reachable
**Steps**:
1. Open Settings.
2. Enter the API base URL and press Enter to save.
3. Navigate to Models and refresh.
4. Verify the model list is fetched from the configured backend.
**Expected Results**:
- Frontend successfully communicates with configured backend

## TEST-MAN-009: Frontend sessions and context
**Purpose**: Validate chat/session creation and maintained context in the UI
**Preconditions**: Frontend running; backend sessions enabled
**Steps**:
1. Create a new session from the left-pane sessions list.
2. Send a prompt and wait for a response.
3. Send a follow-up prompt and verify context continuity.
4. Create or switch to another session.
5. Verify the new session history does not include the previous conversation.
**Expected Results**:
- Context is preserved within a session
- Context does not leak across sessions

## TEST-MAN-010: User-managed provider keys
**Purpose**: Validate per-user commercial provider API keys
**Preconditions**: Frontend and backend running; user key management enabled
**Steps**:
1. Open Profile → Provider Credentials.
2. Add a provider credential (API key or appropriate type).
3. Confirm it appears in the list with masked value.
4. Run a request using a model that targets that provider.
5. Remove or replace the credential and confirm behavior changes.
**Expected Results**:
- Requests succeed with user-provided key
- Key changes take effect immediately and are isolated per user

## TEST-MAN-011: User OSS access keys
**Purpose**: Validate user-created API keys for OSS model access
**Preconditions**: Backend OSS key management enabled
**Steps**:
1. Create a new OSS access key from the UI or API.
2. Call the API using the new key and confirm access.
3. Revoke the key.
4. Retry the API call and confirm access is denied.
**Expected Results**:
- Access granted with valid key
- Access denied after revocation

## TEST-MAN-012: Invite-only registration and authentication
**Purpose**: Validate invite-only registration and login/logout flows
**Preconditions**: Backend running with invite requirement enabled
**Steps**:
1. Launch the app with no saved auth token.
2. Confirm the app shows the Login screen before any other page.
1. Attempt to register without an invite token.
2. Confirm registration is rejected.
3. Register with a valid invite token.
4. Log in and confirm an auth token is issued.
5. Log out and confirm the token is cleared locally.
6. Relaunch the app with a valid auth token saved.
7. Confirm the app lands on Chat instead of Login.
**Expected Results**:
- Unauthenticated users are routed to Login before any app pages
- Registration without invite is rejected
- Registration with invite succeeds
- Login/logout work and auth token is issued/cleared
- Authenticated users land on Chat after launch/login

## TEST-MAN-013: User profile preferences
**Purpose**: Validate profile preferences persistence
**Preconditions**: Authenticated user
**Steps**:
1. Open Profile and set preferred model and UI defaults.
2. Close and reopen the app (or refresh).
3. Verify the preferred model and defaults are applied.
**Expected Results**:
- Preferences are saved and restored
- Preferred model selected by default

## TEST-MAN-014: User API tokens
**Purpose**: Validate user-created API tokens for LLM API access
**Preconditions**: Authenticated user
**Steps**:
1. Create a new API token.
2. Copy the token (shown once) and call the API.
3. Revoke the token.
4. Retry the API call and confirm access is denied.
**Expected Results**:
- Token grants access while active
- Revoked token is rejected

## TEST-MAN-015: UI layout auto-switch and lock
**Purpose**: Validate layout switching by modality/device and user override
**Preconditions**: Frontend running; user profile available
**Steps**:
1. Set layout mode to Auto.
2. Select a text model and verify Chat layout.
3. Switch to image/3D model and verify Studio layout.
4. Resize to mobile width and verify Compact layout.
5. Set mode to Locked and choose a layout.
6. Switch models and confirm layout does not change.
**Expected Results**:
- Text models use Chat layout
- Image/3D use Studio layout
- Mobile uses Compact layout
- Locked/manual modes override auto switching

## TEST-MAN-016: Model download status display
**Purpose**: Validate model cards show download status badges
**Preconditions**: Frontend running; backend running with download worker
**Steps**:
1. Start a model download from the Add Model flow.
2. Observe the model card in the catalog list.
3. Wait for status to update (Downloading → Ready or Failed).
4. Confirm status badges update without a page refresh.
**Expected Results**:
- Downloading models show ⌛ badge with progress
- Completed models show ✓ Ready badge
- Failed models show ⚠ badge with retry option
- Status updates without page refresh

## TEST-MAN-017: Regenerate response
**Purpose**: Validate regenerate/retry functionality
**Preconditions**: Frontend running; completed generation
**Steps**:
1. Generate a response in chat.
2. Click Regenerate on the assistant message.
3. Adjust parameters in settings (optional).
4. Submit regeneration and verify a new response appears.
**Expected Results**:

## TEST-MAN-018: Image inputs in chat
**Purpose**: Validate image upload, paste, and URL attachments for multimodal prompts
**Preconditions**: Frontend running; backend reachable; model that supports image input selected
**Steps**:
1. Attach an image via file upload and send a prompt.
2. Paste an image from clipboard and send a prompt.
3. Provide a valid image URL and send a prompt.
4. Attempt to attach an unsupported file type and verify an error.
5. Attempt to attach a URL blocked by CORS and verify an error.
6. Set the max attachment size to a small value (e.g., 1MB) and try to attach a larger image.
**Expected Results**:
- Attached images are previewed and removable before sending
- Images are sent with the prompt and visible in the user message
- Invalid formats or blocked URLs show a clear error
- Attachment size limit is enforced and configurable

## TEST-MAN-018: Model loading state in UI
**Purpose**: Validate model runtime status display
**Preconditions**: Frontend running; models available
**Steps**:
1. View a model card marked as Unloaded.
2. Click Load and observe loading spinner.
3. Confirm status changes to Loaded.
4. Send a request and verify Busy state appears.
**Expected Results**:
- Status shows: Unloaded → Loading → Loaded → Busy
- Loading shows spinner
- Busy shows queue info

## TEST-MAN-019: Cancel in-flight request
**Purpose**: Validate request cancellation from UI
**Preconditions**: Frontend running; model loaded
**Steps**:
1. Send a request that takes noticeable time.
2. Click Cancel while processing.
3. Confirm the request stops and UI updates.

## TEST-MAN-MVP-001: Add model via Hugging Face search
**Purpose**: Validate add-model flow for Hugging Face search and download
**Automation**: Backend search is covered by `TEST-SYS-MVP-004` in [tests/system/test_mvp_model_search.py](tests/system/test_mvp_model_search.py). Manual run validates UI flow.
**Preconditions**: Frontend running; backend running; Hugging Face reachable
**Steps**:
1. Open Models.
2. Click Add Model.
3. Enter a search query and press Enter.
4. Select a model from the results.
5. Confirm download starts and status appears.
**Expected Results**:
- Results display with model metadata
- Download starts and status updates

## TEST-MAN-MVP-002: Provider credential types
**Purpose**: Validate provider credentials UI for different auth types
**Preconditions**: Authenticated user
**Steps**:
1. Open Profile → Provider Credentials.
2. Add an API key provider and save.
3. Add an endpoint+key provider (e.g., Azure) and save.
4. Add an OAuth token provider (if applicable) and save.
**Expected Results**:
- Fields match provider requirements
- Save succeeds

## TEST-MAN-MVP-003: Left-pane sessions list
**Purpose**: Validate sessions list in left pane and switching
**Automation**: Session contract and naming are covered by `TEST-SYS-MVP-001/002` in [tests/system/test_mvp_sessions_contract.py](tests/system/test_mvp_sessions_contract.py). Manual run validates UI behavior.
**Preconditions**: Sessions available
**Steps**:
1. Open the left-pane Sessions list.
2. Click a session.
3. Verify the chat history switches.
4. Rename a session and confirm list updates.
**Expected Results**:
- Sessions display correctly
- Switching updates context

## TEST-MAN-MVP-004: Message timestamps
**Purpose**: Validate message timestamps display
**Automation**: Message timestamps are covered by `TEST-SYS-MVP-003` in [tests/system/test_mvp_sessions_contract.py](tests/system/test_mvp_sessions_contract.py). Manual run validates UI display.
**Preconditions**: Active session with messages
**Steps**:
1. Send a prompt and receive a response.
2. Verify timestamps show for both user and assistant messages.
**Expected Results**:
- Timestamps rendered for prompts/responses

## TEST-MAN-MVP-005: Settings connection test
**Purpose**: Validate health check button
**Automation**: Health endpoint is covered by `TEST-SYS-004` in [tests/system/test_health_readiness.py](tests/system/test_health_readiness.py). Manual run validates UI indicator.
**Preconditions**: Backend reachable at configured base URL
**Steps**:
1. Open Settings.
2. Click Test Connection.
3. Confirm a green check appears on success.
**Expected Results**:
- Green check on success; error message on failure
3. Observe result
**Expected Results**:
- Cancel button visible during processing
- Request cancelled on click
- UI returns to ready state

## TEST-MAN-020: Queue position indicator
**Purpose**: Validate queue position display
**Preconditions**: Frontend running; model busy
**Steps**:
1. Send multiple requests to queue
2. Observe queue position for each
3. Wait for queue to process
**Expected Results**:
- Queue position shown
- Position updates as queue moves
- Request completes when at front

## Traceability
Requirements → Verification

| Requirement ID | Verification Type | Test/Procedure ID | Location | Notes |
|---|---|---|---|---|
| SYS-REQ-012 | Manual | TEST-MAN-001 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-013 | Manual | TEST-MAN-001 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-003 | Manual | TEST-MAN-002 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-004 | Manual | TEST-MAN-002 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-015 | Manual | TEST-MAN-003 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-025 | Manual | TEST-MAN-004 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-026 | Manual | TEST-MAN-004 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-027 | Manual | TEST-MAN-004 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-028 | Manual | TEST-MAN-005 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-029 | Manual | TEST-MAN-006 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-030 | Manual | TEST-MAN-007 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-031 | Manual | TEST-MAN-008 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-032 | Manual | TEST-MAN-009 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-035 | Manual | TEST-MAN-010 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-036 | Manual | TEST-MAN-011 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-037 | Manual | TEST-MAN-012 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-038 | Manual | TEST-MAN-013 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-039 | Manual | TEST-MAN-014 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-041 | Manual | TEST-MAN-015 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-043 | Manual | TEST-MAN-016 | docs/testing/manual_test_procedures.md | Model status UI |
| SYS-REQ-046 | Manual | TEST-MAN-020 | docs/testing/manual_test_procedures.md | Queue position UI |
| SYS-REQ-047 | Manual | TEST-MAN-019 | docs/testing/manual_test_procedures.md | Cancel UI |
| SYS-REQ-048 | Manual | TEST-MAN-017 | docs/testing/manual_test_procedures.md | Regenerate |
| SYS-REQ-050 | Manual | TEST-MAN-018 | docs/testing/manual_test_procedures.md | Model loading state |
