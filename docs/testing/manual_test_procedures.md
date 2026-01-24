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

## Traceability
Requirements → Verification

| Requirement ID | Verification Type | Test/Procedure ID | Location | Notes |
|---|---|---|---|---|
| SYS-REQ-012 | Manual | TEST-MAN-001 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-013 | Manual | TEST-MAN-001 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-003 | Manual | TEST-MAN-002 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-004 | Manual | TEST-MAN-002 | docs/testing/manual_test_procedures.md | |
| SYS-REQ-015 | Manual | TEST-MAN-003 | docs/testing/manual_test_procedures.md | |
