# Test Specifications

**Project**: Pluggably LLM API Gateway
**Date**: January 24, 2026
**Status**: Complete (Baseline + CR-2026-01-24-03)

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

## Integration Test Specifications

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

## Definition of Ready / Done
**Ready**
- Test cases defined for all key requirements.
- Traceability matrix filled.

**Done**
- Tests implemented and passing.
- Manual test procedures created where needed.
