# Test Specifications — CR-002: API-First Responsibility Refactor

**Project**: Pluggably LLM API Gateway
**Date**: February 17, 2026
**Status**: Proposed (Phase 3 — Awaiting Phase 4 Approval)

## Test Strategy

All changes in CR-002 are testable with automated unit and system tests. No new manual test procedures are required (the existing TEST-MAN-018 for image inputs covers the frontend side).

---

## Unit Tests

### TEST-UNIT-020: Image preprocessing — resize logic
**Traceability**: SYS-REQ-071, US-042
**Description**: Verify the `preprocess_images()` function correctly resizes images based on model constraints.
**Cases**:
1. Image within limits → passed through unchanged, no warnings
2. Image exceeding `max_edge` → resized preserving aspect ratio, warning emitted
3. Image exceeding `max_pixels` but within `max_edge` → resized to fit pixel budget
4. Model has no constraints (`None`) → image passed through unchanged
5. Model has no constraints but provider has defaults → provider defaults used
6. Multiple images, some within limits, some exceeding → only oversized ones resized
7. Non-image data-URL (malformed) → appropriate error raised
8. Various input formats (PNG, JPEG, WebP) → handled correctly
9. Landscape and portrait orientations → aspect ratio preserved in both

### TEST-UNIT-021: Session auto-naming logic
**Traceability**: SYS-REQ-072, US-043
**Description**: Verify that sessions are auto-named on first message.
**Cases**:
1. First message appended to session with no title → title set to first 50 chars of prompt
2. First message with prompt shorter than 50 chars → title is full prompt, trimmed
3. First message with prompt longer than 50 chars → title is first 50 chars, trimmed
4. Session already has a title → title is NOT overwritten on message append
5. Session with messages already (not first) → title is NOT changed
6. First message with empty prompt → title remains None
7. First message with whitespace-only prompt → title remains None

### TEST-UNIT-022: Regenerate endpoint logic
**Traceability**: SYS-REQ-073, US-044
**Description**: Verify the regenerate endpoint's message manipulation logic.
**Cases**:
1. Session with user+assistant messages → last assistant removed, user prompt replayed
2. Session with only user message (no assistant yet) → user prompt replayed, no removal
3. Session with no messages → 400 error
4. Session not found → 404 error
5. Optional model override → generation uses overridden model
6. Optional parameter overrides → generation uses overridden parameters
7. Streaming mode → SSE events returned

### TEST-UNIT-023: Absolute artifact URL generation
**Traceability**: SYS-REQ-074, US-045
**Description**: Verify that artifact URLs are returned as absolute URLs.
**Cases**:
1. Request to `http://localhost:8080` → URLs start with `http://localhost:8080/v1/artifacts/`
2. Request to `https://api.example.com` → URLs start with `https://api.example.com/v1/artifacts/`
3. Multiple artifact URLs → all are absolute
4. 3D artifact URL → absolute

### TEST-UNIT-024: Session message count
**Traceability**: SYS-REQ-075, US-046
**Description**: Verify that session responses include accurate message counts.
**Cases**:
1. New session → message_count is 0
2. Session with 2 messages → message_count is 2
3. After append → message_count increments
4. After reset → message_count is 0
5. List sessions → each session includes message_count

### TEST-UNIT-025: Client library consolidation
**Traceability**: SYS-REQ-076, US-CL-010
**Description**: Verify that the consolidated client has no duplicate model definitions.
**Cases**:
1. `ApiError` is importable from `sdk.dart`
2. `pluggably_client.dart` does not exist
3. All model classes have exactly one definition
4. Frontend compiles with updated imports

---

## System Tests

### TEST-SYS-020: End-to-end image preprocessing
**Traceability**: SYS-REQ-071, US-042
**Description**: Send a generation request with oversized images through the API and verify they are preprocessed.
**Preconditions**: Backend running, at least one model registered with image constraints.
**Steps**:
1. Create a 4096×4096 test image, encode as base64 data-URL
2. Send `POST /v1/generate` with the image in `input.images[]`
3. Verify response includes `warnings` indicating resize occurred
4. Verify the generation completed (image was accepted by backend)
**Expected**: Response contains warnings about resize; generation succeeds.

### TEST-SYS-021: End-to-end session auto-naming
**Traceability**: SYS-REQ-072, US-043
**Description**: Create a session, send a message, verify it's auto-named.
**Steps**:
1. `POST /v1/sessions` → create session (no title)
2. `POST /v1/sessions/{id}/generate` with prompt "Tell me about quantum computing"
3. `GET /v1/sessions/{id}` → verify title is "Tell me about quantum computing"
4. `PUT /v1/sessions/{id}` with title "My Physics Chat"
5. Send another message
6. `GET /v1/sessions/{id}` → verify title is still "My Physics Chat" (not overwritten)
**Expected**: Auto-title on first message; manual title not overwritten.

### TEST-SYS-022: End-to-end regenerate endpoint
**Traceability**: SYS-REQ-073, US-044
**Description**: Send messages in a session, then regenerate the last response.
**Steps**:
1. Create session
2. Send a message, get assistant response
3. Note assistant response content
4. `POST /v1/sessions/{id}/regenerate`
5. Get new assistant response
6. `GET /v1/sessions/{id}` → verify only one assistant message (replaced, not duplicated)
**Expected**: Last assistant message replaced; message count unchanged.

---

## Integration Tests

### TEST-INT-020: Image preprocessing with provider defaults
**Traceability**: SYS-REQ-071
**Description**: Verify that provider-level image defaults are applied when model has no constraints.
**Steps**:
1. Set up a mock OpenAI adapter
2. Send a request with an oversized image to an OpenAI model
3. Verify the image was resized per OpenAI's defaults (max_edge=2048)

---

## Updated Traceability Matrix

| Requirement ID | Verification Type | Test/Procedure ID | Location | Notes |
|---|---|---|---|---|
| SYS-REQ-071 | Automated | TEST-UNIT-020, TEST-SYS-020, TEST-INT-020 | tests/unit/, tests/system/, tests/integration/ | Image preprocessing |
| SYS-REQ-072 | Automated | TEST-UNIT-021, TEST-SYS-021 | tests/unit/, tests/system/ | Auto-naming |
| SYS-REQ-073 | Automated | TEST-UNIT-022, TEST-SYS-022 | tests/unit/, tests/system/ | Regenerate |
| SYS-REQ-074 | Automated | TEST-UNIT-023 | tests/unit/ | Absolute URLs |
| SYS-REQ-075 | Automated | TEST-UNIT-024 | tests/unit/ | Message count |
| SYS-REQ-076 | Automated | TEST-UNIT-025 | clients/dart/test/ | Client consolidation |
| US-FE-020 | Manual | TEST-MAN-018 (existing) | docs/testing/ | Frontend cleanup verified via existing image input test |

## Definition of Ready / Done

**Ready**: All test cases defined with traceability. Test stubs created.

**Done**: All automated tests implemented and passing. No skipped tests remain.
