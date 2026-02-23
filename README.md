# Pluggably LLM API Gateway

A unified API gateway for text, image, and 3D generation supporting commercial providers (OpenAI, Anthropic, Google, Azure, xAI) and local open-source models.

## Quick Start

### Installation

```bash
# Clone and install
cd llm_api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

```bash
# Copy example env file
cp .env.example .env

# Edit with your API key (required)
export LLM_API_API_KEY=your-secret-key
```

### Run the Server

```bash
uvicorn llm_api.main:app --reload --port 8080
```

### Health Check

```bash
curl http://localhost:8080/health
# {"status": "ok"}
```

### Create Users

Users are not created automatically on startup.

Create accounts explicitly:

```bash
python scripts/create_user.py --username hassan --password 'strong-password' --admin
python scripts/create_user.py --username ben --password 'strong-password' --admin
python scripts/create_user.py --username test --password 'strong-password'
```

See [docs/test_credentials.md](docs/test_credentials.md) for details.

---

## Frontend (PlugAI)

The Flutter frontend lives in the frontend/ directory. It connects to the API gateway and provides model browsing, chat, sessions, settings, and key/token management.

Quick start:

```bash
cd frontend
flutter pub get
flutter run -d chrome
```

Then open **Settings** in the app to set the API URL (default: `http://localhost:8000`).

See [frontend/README.md](frontend/README.md) for full usage, tests, and known gaps.

Deployment and release runbooks:
- [docs/ops/deployment.md](docs/ops/deployment.md)
- [docs/ops/supabase_vps_release.md](docs/ops/supabase_vps_release.md)

### Auto-redeploy on `main` / `master`

This repo includes [`.github/workflows/deploy-vps-main.yml`](.github/workflows/deploy-vps-main.yml), which redeploys to the VPS on every push to `main` or `master` (and can be run manually via `workflow_dispatch`).

Set these GitHub repository secrets before enabling it:
- `DEPLOY_SSH_HOST`
- `DEPLOY_SSH_USER`
- `DEPLOY_SSH_KEY` (private key for that user)

The workflow SSHes into the VPS, fast-forwards both server checkouts, and runs:
- `cd /srv/apps/vps-config/llm_api && docker compose up -d --build --remove-orphans`

---

## API Usage Guide

All endpoints require authentication via `X-API-Key` header.

Commercial provider credentials are user-scoped and must be entered via the app’s Profile page.
See [docs/ops/user_provider_credentials.md](docs/ops/user_provider_credentials.md).

### List Configured Providers

```bash
curl -H "X-API-Key: your-key" http://localhost:8080/v1/providers
```

Response (depends on the current user’s saved credentials):
```json
{
  "providers": [
    {"name": "openai", "configured": true, "supported_modalities": ["text"]},
    {"name": "local", "configured": true, "supported_modalities": ["text", "image", "3d"]}
  ]
}
```

### Text Generation

**Using default local model:**
```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "modality": "text",
    "input": {"prompt": "Explain quantum computing in simple terms"}
  }'
```

**Using a specific provider (OpenAI):**
```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "modality": "text",
    "model": "openai:gpt-4",
    "input": {"prompt": "Write a haiku about coding"},
    "parameters": {"temperature": 0.7, "max_tokens": 100}
  }'
```

**Streaming response (SSE):**
```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "modality": "text",
    "input": {"prompt": "Tell me a story"},
    "stream": true
  }'
```

### Image Generation

```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "modality": "image",
    "input": {"prompt": "A sunset over mountains, digital art"}
  }'
```

Response (inline base64 or artifact URL for large images):
```json
{
  "request_id": "abc123",
  "model": "local-image",
  "modality": "image",
  "output": {"images": ["base64-encoded-image-data..."]},
  "usage": {}
}
```

### 3D Generation

```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "modality": "3d",
    "input": {"prompt": "A wooden chair"}
  }'
```

---

## Client Libraries

### Python Client

Install locally from the repo:
```bash
pip install -e clients/python
```

Example:
```python
from llm_api_client import PluggablyClient, GenerateInput, GenerateRequest

client = PluggablyClient("http://localhost:8080", "your-key")
response = client.generate(
    GenerateRequest(
        modality="text",
        input=GenerateInput(prompt="Hello from Python")
    )
)
print(response.output.text)
```

Session helper:
```python
session = client.create_session()
handle = client.session(session.id)
reply = handle.generate(
    GenerateRequest(modality="text", input=GenerateInput(prompt="Hi"))
)
```

### Dart/Flutter Client

Add to your Dart/Flutter project using a path dependency:
```yaml
dependencies:
  pluggably_llm_client:
    path: ../llm_api/clients/dart
```

Example:
```dart
import 'package:pluggably_llm_client/pluggably_client.dart';

final client = PluggablyClient(baseUrl: 'http://localhost:8080', apiKey: 'your-key');
final response = await client.generate(
  GenerateRequest(
    modality: 'text',
    input: GenerateInput(prompt: 'Hello from Dart'),
  ),
);
print(response.output['text']);
```

Session helper:
```dart
final session = await client.createSession();
final reply = await client.generateWithSession(
  session.id,
  GenerateRequest(modality: 'text', input: GenerateInput(prompt: 'Hi')),
);
```

## Model Management

### List Available Models

```bash
curl -H "X-API-Key: your-key" http://localhost:8080/v1/models
```

Filter by modality:
```bash
curl -H "X-API-Key: your-key" "http://localhost:8080/v1/models?modality=text"
```

### Download a Local Model

Download a model from Hugging Face:
```bash
curl -X POST http://localhost:8080/v1/models/download \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": {
      "id": "mistral-7b",
      "name": "Mistral 7B",
      "version": "1.0",
      "modality": "text"
    },
    "source": {
      "type": "huggingface",
      "id": "TheBloke/Mistral-7B-v0.1-GGUF"
    },
    "options": {
      "revision": "main"
    }
  }'
```

Response:
```json
{
  "job_id": "job-123",
  "model_id": "mistral-7b",
  "status": "queued",
  "progress_pct": 0,
  "created_at": "2026-01-24T12:00:00Z"
}
```

### Search Hugging Face Models

```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:8080/v1/models/search?source=huggingface&query=llama"
```

Response:
```json
{
  "results": [
    {
      "id": "meta-llama/Llama-3",
      "name": "meta-llama/Llama-3",
      "tags": ["text-generation"],
      "modality_hints": ["text"],
      "downloads": 100,
      "last_modified": "2026-01-26T00:00:00Z"
    }
  ],
  "next_cursor": "20"
}
```

### Check Download Progress

```bash
curl -H "X-API-Key: your-key" http://localhost:8080/v1/jobs/job-123
```

### Cancel a Download

```bash
curl -X DELETE -H "X-API-Key: your-key" http://localhost:8080/v1/jobs/job-123
```

---

## Provider Configuration

Configure commercial providers by setting environment variables in `.env`:

| Provider | Environment Variables |
|----------|----------------------|
| OpenAI | `LLM_API_OPENAI_API_KEY` |
| Anthropic | `LLM_API_ANTHROPIC_API_KEY` |
| Google | `LLM_API_GOOGLE_API_KEY` |
| Azure | `LLM_API_AZURE_OPENAI_API_KEY`, `LLM_API_AZURE_OPENAI_ENDPOINT` |
| xAI | `LLM_API_XAI_API_KEY` |

See [docs/ops/provider_keys.md](docs/ops/provider_keys.md) for detailed setup instructions.

---

## Local Runtime Setup

For running models locally without commercial APIs:

| Modality | Runtime | Setup |
|----------|---------|-------|
| Text | llama.cpp | Install `llama-cpp-python`, set `LLM_API_LOCAL_TEXT_MODEL_PATH` |
| Image | Diffusers | Install `diffusers torch`, set `LLM_API_LOCAL_IMAGE_MODEL_ID` |
| 3D | Shap-E | Install `shap-e`, set `LLM_API_LOCAL_3D_MODEL_ID` |

See [docs/ops/local_runtimes.md](docs/ops/local_runtimes.md) for detailed setup.

---

## Deployment

See [docs/ops/deployment.md](docs/ops/deployment.md) for:
- Local server deployment (Docker, systemd)
- Cloud deployment (free and paid options)
- Scaling strategies

---

## Monitoring

### Metrics Endpoint

```bash
curl http://localhost:8080/metrics
```

Returns Prometheus-format metrics:
```
llm_api_request_count 42
llm_api_error_count 2
llm_api_latency_ms_count 42
llm_api_latency_ms_sum 1234.5
```

### Readiness Check

```bash
curl http://localhost:8080/ready
# {"status": "ready"} or 503 if not ready
```

---

## Documentation

- [API Contract (OpenAPI)](docs/contracts/openapi.yaml)
- [Provider Keys Setup](docs/ops/provider_keys.md)
- [Local Runtimes Setup](docs/ops/local_runtimes.md)
- [Deployment Guide](docs/ops/deployment.md)
- [Architecture](docs/architecture/system_architecture.md)

---

## Development

Run tests:
```bash
pytest -q
```

Generate test reports (backend JUnit + Flutter JSON):
```bash
./scripts/generate_test_report.sh
```

Reports are written to:
- reports/pytest.xml
- reports/flutter_test.json

Run with auto-reload:
```bash
uvicorn llm_api.main:app --reload
```

