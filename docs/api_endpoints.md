# API Endpoint Reference

This document provides a quick reference for all API endpoints in the LLM API Gateway.

## Authentication

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
Authorization: Bearer <token>
```

### Get Model
```
GET /v1/models/{model_id}
Authorization: Bearer <token>
```

### Get Model Schema
```
GET /v1/schema?model={model_id}
Authorization: Bearer <token>
```

## Model Lifecycle

### Get Model Status
```
GET /v1/models/{model_id}/status
Authorization: Bearer <token>
```

### Load Model
```
POST /v1/models/{model_id}/load
Authorization: Bearer <token>
Content-Type: application/json

{
  "wait": true,
  "use_fallback": false
}
```

### Unload Model
```
POST /v1/models/{model_id}/unload
Authorization: Bearer <token>
Content-Type: application/json

{
  "force": false
}
```

### List Loaded Models
```
GET /v1/models/loaded
Authorization: Bearer <token>
```

## Generation

### Generate (Non-Streaming)
```
POST /v1/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "model": "model-id",
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

### Generate (Streaming)
```
POST /v1/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "model": "model-id",
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
Authorization: Bearer <token>
```

### List Sessions
```
GET /v1/sessions
Authorization: Bearer <token>
```

### Get Session
```
GET /v1/sessions/{session_id}
Authorization: Bearer <token>
```

### Update Session
```
PUT /v1/sessions/{session_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "New Title"
}
```

### Delete Session
```
DELETE /v1/sessions/{session_id}
Authorization: Bearer <token>
```

### Reset Session
```
POST /v1/sessions/{session_id}/reset
Authorization: Bearer <token>
```

## Requests

### Get Request Status
```
GET /v1/requests/{request_id}/status
Authorization: Bearer <token>
```

### Cancel Request
```
POST /v1/requests/{request_id}/cancel
Authorization: Bearer <token>
```

## User API Tokens

### List Tokens
```
GET /v1/users/tokens
Authorization: Bearer <token>
```

### Create Token
```
POST /v1/users/tokens
Authorization: Bearer <token>
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
Authorization: Bearer <token>
```

## Provider Keys

### List Provider Keys
```
GET /v1/users/provider-keys
Authorization: Bearer <token>
```

### Add Provider Key
```
POST /v1/users/provider-keys
Authorization: Bearer <token>
Content-Type: application/json

{
  "provider": "openai",
  "api_key": "sk-..."
}
```

### Delete Provider Key
```
DELETE /v1/users/provider-keys/{provider}
Authorization: Bearer <token>
```

## User Profile

### Get Profile
```
GET /v1/users/me
Authorization: Bearer <token>
```

### Update Profile
```
PATCH /v1/users/me
Authorization: Bearer <token>
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
