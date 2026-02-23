# API Endpoint Reference

This document provides a quick reference for all API endpoints in the LLM API Gateway.

## Authentication

All endpoints require the `X-API-Key` header. User login (if enabled) provides a session token used by the frontend, but API access uses `X-API-Key`.

### Register User
```
POST /v1/users/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "invite_token": "optional-if-invite-required-is-true"
}
```

### Login
```
POST /v1/users/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response: {
  "token": "session-token",
  "user": {...}
}
```

## Models

### List Models
```
GET /v1/models
X-API-Key: <token>
```

### Get Model
```
GET /v1/models/{model_id}
X-API-Key: <token>
```

### Get Model Schema
```
GET /v1/schema?model={model_id}
X-API-Key: <token>
```

### Set Default Model (per modality)
```
POST /v1/models/{model_id}/default
X-API-Key: <token>
```

## Model Lifecycle

### Get Model Status
```
GET /v1/models/{model_id}/status
X-API-Key: <token>
```

### Load Model
```
POST /v1/models/{model_id}/load
X-API-Key: <token>
Content-Type: application/json

{
  "wait": true,
  "use_fallback": false
}
```

### Unload Model
```
POST /v1/models/{model_id}/unload
X-API-Key: <token>
Content-Type: application/json

{
  "force": false
}
```

### List Loaded Models
```
GET /v1/models/loaded
X-API-Key: <token>
```

## Generation

### Generate (Non-Streaming)
```
POST /v1/generate
X-API-Key: <token>
Content-Type: application/json

{
  "model": "model-id",
  "provider": "openai",
  "modality": "text",
  "input": {
    "prompt": "Hello, how are you?"
  },
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 100
  },
  "session_id": "optional-session-id"
}
```

Notes:
- If `model` is omitted, you may specify `provider` to let the backend select a suitable model.
- Responses may include selection metadata and credit/usage status when available.

### Generate (Streaming)
```
POST /v1/generate
X-API-Key: <token>
Content-Type: application/json

{
  "model": "model-id",
  "provider": "openai",
  "modality": "text",
  "input": {
    "prompt": "Hello, how are you?"
  },
  "stream": true,
  "session_id": "optional-session-id"
}

Response: Server-Sent Events (SSE)
```

## Sessions

### Create Session
```
POST /v1/sessions
X-API-Key: <token>
```

### List Sessions
```
GET /v1/sessions
X-API-Key: <token>
```

### Get Session
```
GET /v1/sessions/{session_id}
X-API-Key: <token>
```

### Update Session
```
PUT /v1/sessions/{session_id}
X-API-Key: <token>
Content-Type: application/json

{
  "title": "New Title"
}
```

### Delete Session
```
DELETE /v1/sessions/{session_id}
X-API-Key: <token>
```

### Reset Session
```
POST /v1/sessions/{session_id}/reset
X-API-Key: <token>
```

## Requests

### Get Request Status
```
GET /v1/requests/{request_id}/status
X-API-Key: <token>
```

### Cancel Request
```
POST /v1/requests/{request_id}/cancel
X-API-Key: <token>
```

## User API Tokens

### List Tokens
```
GET /v1/users/tokens
X-API-Key: <token>
```

### Create Token
```
POST /v1/users/tokens
X-API-Key: <token>
Content-Type: application/json

{
  "name": "My Token",
  "scopes": ["read", "write"],
  "expires_days": 30
}
```

### Revoke Token
```
DELETE /v1/users/tokens/{token_id}
X-API-Key: <token>
```

## Provider Keys

Provider keys are user-scoped and unlock commercial models for that user.

### List Provider Keys
```
GET /v1/users/provider-keys
X-API-Key: <token>
```

### Add Provider Key
```
POST /v1/users/provider-keys
X-API-Key: <token>
Content-Type: application/json

{
  "provider": "openai",
  "api_key": "sk-..."
}
```

### Delete Provider Key
```
DELETE /v1/users/provider-keys/{provider}
X-API-Key: <token>
```

## User Profile

### Get Profile
```
GET /v1/users/me
X-API-Key: <token>
```

### Update Profile
```
PATCH /v1/users/me
X-API-Key: <token>
Content-Type: application/json

{
  "display_name": "New Name"
}
```

## Providers

### List Providers
```
GET /v1/providers
Authorization: Bearer <token>
```

## Health & Metrics

### Health Check
```
GET /health
```

### Readiness Check
```
GET /ready
```

### Metrics
```
GET /metrics
```
