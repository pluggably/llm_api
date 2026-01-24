# Detailed Design — Client Library

**Project**: Pluggably LLM API Gateway
**Component**: Client Library
**Date**: January 24, 2026
**Status**: Approved (Baseline + CR-2026-01-24-03)

## Overview
Defines client-side data models, transport, and session helper behavior for Python and Dart/Flutter clients.

## Data Structures (Sketch)

### Client Configuration
```yaml
base_url: string
api_key: string
timeout_seconds: number
retries: number
```

### Dart/Flutter Configuration
```yaml
base_url: string
api_key: string
timeout_seconds: number
```

### Generate Request/Response
Matches server schema from OpenAPI; include `session_id` and `state_tokens` fields.

## Flow
1. Serialize typed request.
2. Add auth headers.
3. Send HTTP request.
4. Deserialize response to typed model.

## Error Handling
- Map HTTP errors to SDK exceptions.
- Provide access to error code, message, and HTTP status.

## Session Helpers
- create_session()
- list_sessions()
- get_session(session_id)
- reset_session(session_id)
- close_session(session_id)

## Traceability
Requirements → Design

| Requirement ID | Design Section | Notes |
|---|---|---|
| SYS-REQ-023 | Data Structures, Flow | |
| SYS-REQ-024 | Session Helpers | |

## Definition of Ready / Done
**Ready**
- Models and endpoints defined.

**Done**
- SDK behavior matches server contract.
- Unit tests cover serialization and session helpers.
