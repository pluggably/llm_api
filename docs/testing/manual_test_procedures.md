# Manual Test Procedures

**Project**: Pluggably LLM API Gateway
**Date**: January 24, 2026
**Status**: Ready for Execution

## TEST-MAN-001: Large model download on constrained host
**Purpose**: Validate long-running download behavior and disk usage handling
**Preconditions**: Server running; limited disk quota configured
**Steps**:
1. Trigger download of a large model (e.g., multi-GB)
2. Observe progress status endpoint
3. Let download complete or exceed storage limit
**Expected Results**:
- Status updates show progress
- If storage limit is exceeded, download fails gracefully with a clear error
- Registry reflects final status

## TEST-MAN-002: GPU-only model execution
**Purpose**: Validate local runner on GPU-only model
**Preconditions**: Host with GPU, compatible drivers, model available
**Steps**:
1. Download a GPU-only model
2. Execute a request using that model
**Expected Results**:
- Response generated successfully
- Logs include hardware backend info

## TEST-MAN-003: Artifact download via URL
**Purpose**: Validate artifact URL response flow
**Preconditions**: Artifact store enabled
**Steps**:
1. Generate image/3D output that exceeds inline payload limit
2. Receive response with artifact URL
3. Download artifact via URL
**Expected Results**:
- URL is valid and downloadable
- URL expires after configured TTL

## TEST-MAN-004: Frontend model selection and dynamic parameters
**Purpose**: Validate model selection and schema-driven parameter panel
**Preconditions**: Frontend running; backend running; API key configured
**Steps**:
1. Open the frontend and select a text model
2. Open the settings pane and confirm parameter inputs render from schema
3. Switch to an image model and confirm parameters update dynamically
**Expected Results**:
- Model list and modality filtering work
- Parameter panel updates with the selected model schema

## TEST-MAN-005: Text chat UI streaming
**Purpose**: Validate streaming responses in the chat UI
**Preconditions**: Frontend running; backend streaming enabled
**Steps**:
1. Select a text model
2. Send a prompt in the chat UI
3. Observe streaming response in the chat bubble
**Expected Results**:
- Response appears incrementally in the UI

## TEST-MAN-006: Image generation UI
**Purpose**: Validate image generation gallery and download
**Preconditions**: Frontend running; image model available
**Steps**:
1. Select an image model and enter a prompt
2. Generate images and observe the gallery
3. Download an image
**Expected Results**:
- Images display in a gallery
- Download succeeds

## TEST-MAN-007: 3D generation UI
**Purpose**: Validate 3D preview and download
**Preconditions**: Frontend running; 3D model available
**Steps**:
1. Select a 3D model and enter a prompt
2. Generate and view the 3D preview
3. Download the 3D asset
**Expected Results**:
- 3D viewer renders and supports interaction
- Download succeeds

## TEST-MAN-008: Separate hosting configuration
**Purpose**: Validate frontend API base URL configuration
**Preconditions**: Frontend hosted separately; backend reachable
**Steps**:
1. Configure API base URL in frontend settings
2. Verify requests go to the configured backend
**Expected Results**:
- Frontend successfully communicates with configured backend

## TEST-MAN-009: Frontend sessions and context
**Purpose**: Validate chat/session creation and maintained context in the UI
**Preconditions**: Frontend running; backend sessions enabled
**Steps**:
1. Create a new chat session
2. Send a prompt and receive a response
3. Send a follow-up prompt in the same session
4. Switch to a new session and verify context isolation
**Expected Results**:
- Context is preserved within a session
- Context does not leak across sessions

## TEST-MAN-010: User-managed provider keys
**Purpose**: Validate per-user commercial provider API keys
**Preconditions**: Frontend and backend running; user key management enabled
**Steps**:
1. Enter a commercial provider key in user settings
2. Run a request targeting that provider
3. Remove or replace the key
**Expected Results**:
- Requests succeed with user-provided key
- Key changes take effect immediately and are isolated per user

## TEST-MAN-011: User OSS access keys
**Purpose**: Validate user-created API keys for OSS model access
**Preconditions**: Backend OSS key management enabled
**Steps**:
1. Create a new OSS access key
2. Use the key to call the API
3. Revoke the key and retry
**Expected Results**:
- Access granted with valid key
- Access denied after revocation

## TEST-MAN-012: Invite-only registration and authentication
**Purpose**: Validate invite-only registration and login/logout flows
**Preconditions**: Backend running with invite requirement enabled
**Steps**:
1. Attempt registration without invite token
2. Register with a valid invite token
3. Log in and log out
**Expected Results**:
- Registration without invite is rejected
- Registration with invite succeeds
- Login/logout work and auth token is issued/cleared

## TEST-MAN-013: User profile preferences
**Purpose**: Validate profile preferences persistence
**Preconditions**: Authenticated user
**Steps**:
1. Set preferred model and UI defaults
2. Restart app or refresh session
3. Confirm preferences persist and apply
**Expected Results**:
- Preferences are saved and restored
- Preferred model selected by default

## TEST-MAN-014: User API tokens
**Purpose**: Validate user-created API tokens for LLM API access
**Preconditions**: Authenticated user
**Steps**:
1. Create a new API token
2. Use the token to call the API
3. Revoke the token and retry
**Expected Results**:
- Token grants access while active
- Revoked token is rejected

## TEST-MAN-015: UI layout auto-switch and lock
**Purpose**: Validate layout switching by modality/device and user override
**Preconditions**: Frontend running; user profile available
**Steps**:
1. Enable auto mode and select a text model
2. Switch to an image/3D model
3. Test on mobile viewport
4. Lock a layout and verify no auto-switching
**Expected Results**:
- Text models use Chat layout
- Image/3D use Studio layout
- Mobile uses Compact layout
- Locked/manual modes override auto switching

## TEST-MAN-016: Model download status display
**Purpose**: Validate model cards show download status badges
**Preconditions**: Frontend running; backend running with download worker
**Steps**:
1. Trigger a model download from the UI or API
2. Observe the model card in the catalog
3. Wait for download to complete or fail
4. Verify status badge updates
**Expected Results**:
- Downloading models show ⌛ badge with progress
- Completed models show ✓ Ready badge
- Failed models show ⚠ badge with retry option
- Status updates without page refresh

## TEST-MAN-017: Regenerate response
**Purpose**: Validate regenerate/retry functionality
**Preconditions**: Frontend running; completed generation
**Steps**:
1. Generate a response
2. Click regenerate button
3. Optionally modify parameters
4. Submit regeneration
**Expected Results**:
- New response generated
- Option to keep or replace original
- Modified parameters applied

## TEST-MAN-018: Model loading state in UI
**Purpose**: Validate model runtime status display
**Preconditions**: Frontend running; models available
**Steps**:
1. View unloaded model card
2. Click "Load" button
3. Observe loading state
4. Verify loaded state
5. Send request and observe busy state
**Expected Results**:
- Status shows: Unloaded → Loading → Loaded → Busy
- Loading shows spinner
- Busy shows queue info

## TEST-MAN-019: Cancel in-flight request
**Purpose**: Validate request cancellation from UI
**Preconditions**: Frontend running; model loaded
**Steps**:
1. Send a request
2. Click cancel button while processing
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
