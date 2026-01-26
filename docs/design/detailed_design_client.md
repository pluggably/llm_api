# Detailed Design — Client Library

**Project**: Pluggably LLM API Gateway + PlugAI Frontend
**Component**: Client Library
**Date**: January 26, 2026
**Status**: Updated (Pending Approval)

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

### User Provider Key Model
```yaml
id: string
provider: string
label: string
created_at: datetime
```

### OSS Access Key Model
```yaml
id: string
label: string
status: [active|revoked]
created_at: datetime
```

### User Profile Model
```yaml
id: string
email: string
preferences: object
created_at: datetime
```

### User API Token Model
```yaml
id: string
label: string
status: [active|revoked]
created_at: datetime
```

### Session Summary Model
```yaml
id: string
title: string|null
created_at: datetime
last_used_at: datetime
```

### Message Model
```yaml
id: string
role: user|assistant
content: string
created_at: datetime
```

### Hugging Face Search Result
```yaml
id: string
name: string
tags: [string]
modality_hints: [text|image|3d]
```

### Health Check Response
```yaml
status: string
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

## Key Management Helpers
- list_provider_keys()
- create_provider_key(provider, label, key)
- delete_provider_key(key_id)
- list_oss_keys()
- create_oss_key(label)
- revoke_oss_key(key_id)

## Auth/Profile Helpers
- register_with_invite(email, password, invite_token)
- login(email, password)
- logout()
- get_profile()
- update_profile(preferences)

## User API Token Helpers
- list_user_tokens()
- create_user_token(label)
- revoke_user_token(token_id)

## Model Search Helpers
- search_models(query, source="huggingface", modality?)

## Health Check Helper
- get_health()

## Traceability
Requirements → Design

| Requirement ID | Design Section | Notes |
|---|---|---|
| SYS-REQ-023 | Data Structures, Flow | |
| SYS-REQ-024 | Session Helpers | |
| SYS-REQ-035 | Key Management Helpers | |
| SYS-REQ-036 | Key Management Helpers | |
| SYS-REQ-037 | Auth/Profile Helpers | |
| SYS-REQ-038 | Auth/Profile Helpers | |
| SYS-REQ-039 | User API Token Helpers | |
| SYS-REQ-063 | Model Search Helpers | |
| SYS-REQ-065 | Session Summary Model | |
| SYS-REQ-066 | Session Summary Model | |
| SYS-REQ-067 | Message Model | |
| SYS-REQ-068 | Health Check Helper | |

## Definition of Ready / Done
**Ready**
- Models and endpoints defined.

**Done**
- SDK behavior matches server contract.
- Unit tests cover serialization and session helpers.
