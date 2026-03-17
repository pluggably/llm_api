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

Supported providers: `openai`, `anthropic`, `google`, `azure`, `xai`, `deepseek`, `groq`, `huggingface`, `local`.
Models can be specified by name (auto-detected) or as `provider:model` (e.g. `groq:llama-3.3-70b-versatile`).

### Generate (Non-Streaming)
```
POST /v1/generate
X-API-Key: <token>
Content-Type: application/json

{
  "model": "gpt-4o",
  "provider": "openai",
  "modality": "text",
  "input": {
    "prompt": "Hello, how are you?"
  },
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 1024
  },
  "system_prompt": "You are a helpful assistant.",
  "session_id": "optional-session-id"
}
```

Notes:
- If `model` is omitted, specify `provider` to let the backend select a suitable model.
- `selection_mode` controls routing: `auto` (default), `free_only`, `commercial_only`, `model`.
- Responses include `selection` metadata (which model/provider was used and whether a fallback occurred) and optionally `credits_status`.

### Provider Examples
```json
// Groq (fast inference)
{ "provider": "groq", "modality": "text", "input": { "prompt": "..." } }

// DeepSeek
{ "provider": "deepseek", "modality": "text", "input": { "prompt": "..." } }

// xAI Grok
{ "provider": "xai", "modality": "text", "input": { "prompt": "..." } }

// Azure OpenAI (requires endpoint_key credential)
{ "provider": "azure", "modality": "text", "input": { "prompt": "..." } }
```

### Generate (Streaming)
```
POST /v1/generate
X-API-Key: <token>
Content-Type: application/json

{
  "provider": "groq",
  "modality": "text",
  "input": {
    "prompt": "Tell me a story"
  },
  "stream": true
}

Response: Server-Sent Events (SSE)
// First event: {"event": "model_selected", "model": "...", "provider": "groq", ...}
// Text chunks: {"text": "...", "done": false}
// Final: data: [DONE]
```

## Sessions

### Create Session
```
POST /v1/sessions
X-API-Key: <token>
Content-Type: application/json

{
  "title": "Optional title",
  "system_prompt": "Optional system prompt for all messages in this session"
}
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

### Delete (Close) Session
```
DELETE /v1/sessions/{session_id}
X-API-Key: <token>
```

### Reset Session Context
```
POST /v1/sessions/{session_id}/reset
X-API-Key: <token>
```

### Generate With Session
```
POST /v1/sessions/{session_id}/generate
X-API-Key: <token>
Content-Type: application/json

{ "modality": "text", "input": { "prompt": "Continue the story..." } }
```

### Regenerate Last Response
```
POST /v1/sessions/{session_id}/regenerate
X-API-Key: <token>
Content-Type: application/json

{
  "model": "optional-override-model",
  "stream": false
}
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

// Simple API key (OpenAI, Anthropic, Google, xAI, DeepSeek, Groq, HuggingFace)
{
  "provider": "groq",
  "credential_type": "api_key",
  "api_key": "gsk_..."
}

// Azure OpenAI (requires endpoint)
{
  "provider": "azure",
  "credential_type": "endpoint_key",
  "api_key": "<azure-key>",
  "endpoint": "https://<resource>.openai.azure.com/"
}

// Google service account
{
  "provider": "google",
  "credential_type": "service_account",
  "service_account_json": "{...}"
}
```

Supported providers: `openai`, `anthropic`, `google`, `azure`, `xai`, `deepseek`, `groq`, `huggingface`.

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
X-API-Key: <token>
```

Returns each provider's name, whether credentials are configured for the current user, and supported modalities.

## Features

### Get Feature Flags
```
GET /v1/features
X-API-Key: <token>
```

Returns backend capability flags used by the frontend (e.g. `local_models_enabled`, `huggingface_hosted_3d_supported`).

## Model Search

### Search Hugging Face Models
```
GET /v1/models/search?query=llama&source=huggingface&limit=20
X-API-Key: <token>
```

Parameters: `query` (required), `source` (default: huggingface), `modality` (text/image/3d), `limit`, `cursor`.

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
