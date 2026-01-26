# PlugAI Roadmap

**Project**: Pluggably LLM API Gateway + Cross-Platform Frontend (PlugAI)
**Date**: January 24, 2026
**Status**: Living Document

## Release Overview

| Version | Status | Description |
|---------|--------|-------------|
| v1.0 | In Development | Full-featured MVP with model lifecycle, auth, and UI |
| v2.0 | Planned | Advanced features and operational maturity |

---

## v1.0 - Initial Release (Current Focus)

### Core Features
- ✅ Standard multimodal API (text/image/3D)
- ✅ Provider adapters (OpenAI, Anthropic, Google, Azure, xAI)
- ✅ Local model runner (llama.cpp, diffusers, shap-e)
- ✅ Model registry with auto-discovery
- ✅ Session management (multi-turn conversations)
- ✅ Streaming responses (SSE)
- ✅ Artifact storage for large outputs

### User Management
- ✅ Invite-only registration
- ✅ User authentication (API key + JWT/OAuth)
- ✅ User profiles with preferences
- ✅ Per-user provider API keys
- ✅ User-created API tokens

### Model Lifecycle (New)
- ✅ Model loading/unloading with idle timeout
- ✅ Default pinned model (always loaded)
- ✅ Concurrent model limits with LRU eviction
- ✅ Prepare/load model endpoint
- ✅ Model runtime status (unloaded/loading/loaded/busy)
- ✅ Get loaded models endpoint
- ✅ Background downloads with status and deduplication
- ✅ Hugging Face documentation enrichment

### Request Management (New)
- ✅ Request queueing with position feedback
- ✅ Request cancellation
- ✅ Regenerate/retry responses
- ✅ Fallback model configuration

### Frontend
- ✅ Cross-platform Flutter UI (web + mobile)
- ✅ Model selection with modality filtering
- ✅ Dynamic parameter panel from schema
- ✅ Chat UI with streaming
- ✅ Image gallery UI
- ✅ 3D viewer UI
- ✅ Session management UI
- ✅ Model download status badges
- ✅ Model loading state indicators
- ✅ Cancel button for in-flight requests
- ✅ Regenerate button
- ✅ Queue position indicator
- ✅ Pre-load model button
- ✅ UI layout auto-switch by modality/device

### Frontend (MVP gaps)
- [ ] Add-model workflow with search/filter by modality or use-case.
- [ ] Profile UI for commercial provider credentials (API keys + non-key auth types).
- [ ] Sessions list parsing fixes (frontend + API contract alignment).

### Client SDKs
- ✅ Python client library
- ✅ Dart/Flutter client library
- ✅ Typed request/response models
- ✅ Session helpers
- ✅ Model lifecycle methods
- ✅ Request cancellation
- ✅ Queue status queries

---

## v2.0 - Future Release

### Cost & Usage Management
- [ ] **Cost Tracking**: Track token usage per user with cost estimates
- [ ] **Usage Quotas**: Set per-user or per-model usage limits
- [ ] **Usage Dashboard**: Visualize usage patterns and costs
- [ ] **Billing Integration**: Optional integration with payment providers

### Audit & Compliance
- [ ] **Audit Log**: Comprehensive logging of who requested what, when
- [ ] **Request History**: Queryable history of all requests per user
- [ ] **Data Retention Policies**: Configurable retention for prompts/responses
- [ ] **Export/Import Sessions**: Export conversations to JSON/Markdown

### Advanced Model Features
- [ ] **Model Comparison**: Side-by-side output comparison from different models
- [ ] **Prompt Templates**: Saved system prompts and templates per user
- [ ] **Model Aliases**: User-defined aliases for model selection
- [ ] **Fine-tuned Model Support**: Host and serve fine-tuned models

### Performance & Scalability
- [ ] **WebSocket Support**: Real-time updates for downloads, status, queues
- [ ] **Response Caching**: Cache identical requests (temperature=0)
- [ ] **Batch Processing API**: Process multiple requests in one call
- [ ] **Model Preloading**: Background warm-up of frequently used models
- [ ] **Rate Limiting**: Per-user and per-model rate limits

### Operations
- [ ] **Granular Health Checks**: Per-provider health status
- [ ] **Error Code Enum**: Standardized error codes with documentation
- [ ] **Kubernetes Deployment**: Helm charts and horizontal scaling
- [ ] **Multi-node Support**: Distributed model loading across nodes

### Security
- [ ] **API Key Rotation**: Rotate keys without downtime
- [ ] **CORS Policy Configuration**: Configurable allowed origins
- [ ] **CSP Headers**: Content Security Policy for web frontend
- [ ] **Input Sanitization**: Explicit prompt sanitization rules
- [ ] **MFA Support**: Multi-factor authentication option

### UI Enhancements
- [ ] **Dark Mode**: System-aware and manual toggle
- [ ] **Keyboard Shortcuts**: Power user navigation
- [ ] **Accessibility Improvements**: Full WCAG AA compliance
- [ ] **Offline Mode**: Queue requests when offline
- [ ] **Model Favorites**: Pin frequently used models

---

## Backlog (Unscheduled)

These items are captured but not yet prioritized:

- Voice input/output for chat
- Plugin/extension system for custom adapters
- Multi-language UI localization
- Model performance benchmarking
- A/B testing for prompt variations
- Collaborative sessions (shared context)
- Model recommendation engine
- Integration with vector databases for RAG
- Image editing/inpainting workflows
- Video generation support
- Session naming
- Message/prompt timestamping in sessions
- Settings connection test button

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-24 | Include model lifecycle in v1.0 | Critical for UX with local models |
| 2026-01-24 | Include request queueing in v1.0 | Required for multi-user local inference |
| 2026-01-24 | Defer cost tracking to v2.0 | Not critical for initial adoption |
| 2026-01-24 | Defer audit log to v2.0 | Compliance not required for personal use |
| 2026-01-24 | Defer batch processing to v2.0 | Power user feature, not MVP |

---

## Contributing

To propose a new feature:
1. Add it to the Backlog section with a brief description
2. Discuss priority and scope in a PR or issue
3. If approved, move to appropriate version section

---

**Last Updated**: January 26, 2026
