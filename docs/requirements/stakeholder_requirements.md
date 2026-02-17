# Stakeholder Requirements

**Project**: Pluggably LLM API Gateway + Cross-Platform Frontend (working name: PlugAI)
**Date**: January 26, 2026
**Status**: Updated (Pending Approval)

## Problem Statement
I need a single, standard API and a cross-platform UI that I can host on a home server or in the cloud to interface with many LLM providers and local/open-source models. The API should abstract provider differences and enable a consistent client experience, while the frontend should offer a chat-like interface with model selection and dynamic parameter controls.

## Stakeholders / Personas
- **Primary User/Operator**: You (developer/owner running on home server or cloud)
- **End Users**: People who use the UI to interact with text, image, and 3D models
- **API Consumers**: Apps or scripts calling the standard API
- **Model Providers**: Commercial APIs, free/public APIs (if available), local OSS models

## Business Objectives
- Provide a unified API surface for multiple LLM backends.
- Provide a cross-platform UI (web + mobile) for model interaction.
- Allow rapid switching between providers/models without client changes.
- Enable local/offline or cost-optimized model hosting.

## User Needs
- Standardized API that works with commercial, free, and local OSS LLMs.
- Cross-platform UI to interact with models without writing code.
- Ability to run models locally (e.g., DeepSeek) or specialized models (e.g., image or 3D generation).
- Hosting flexibility: home server or cloud deployment.
- Model selection and configuration UI with dynamic parameters per model.
- Chat-like interface for text models and modality-appropriate UI for image/3D.
- Attach images to prompts via upload, paste, or URL for models that support image input.
- Help with model hosting infrastructure and API integration logic.
- Per-user sessions with persistent conversational context.
- Per-user API keys (commercial providers) and OSS model access controls.
- A model registry that tracks internal/external models and supported parameters.
- User authentication (login/logout) with invite-only registration.
- User profiles with preferences (preferred models, UI defaults).
- User-created API tokens for direct API access.
- Auto-enrich model entries with Hugging Face documentation and parameter guidance when available.
- UI that adapts to modality (chat vs studio) and device (mobile), with user override.
- Non-blocking model downloads with status and reuse of existing models.
- Model loading/unloading management with a default model always ready.
- Ability to pre-load models before making requests to avoid cold-start latency.
- Request queueing when resources are busy, with feedback on queue position.
- Ability to cancel long-running requests.
- Ability to regenerate/retry responses.
- Option to fall back to a default model while requested model is loading, or choose to wait for the requested model.
- Add models from the UI by searching Hugging Face and downloading new models; include text search to filter large model lists.
- Manage commercial provider credentials from the profile UI, including non-API-key auth types when required.
- Manage and switch sessions from the left-pane sessions list (no separate sessions page), with reliable display.
- Name sessions for easier organization.
- Track timestamps for prompts/commands/messages within sessions.
- Test API connectivity from the settings UI (health endpoint success shown with a green check).

## High-Level Functional Requirements (Stakeholder)
- **SH-REQ-001**: Provide a single, standard HTTP API for text, image, and 3D generation (multimodal).
- **SH-REQ-002**: Support configurable backends for commercial, free/public, and local OSS models.
- **SH-REQ-003**: Enable local model hosting and inference for a broad range of OSS models (pluggable runners; “any model” where technically feasible).
- **SH-REQ-004**: Support non-text models (image generation, 3D generation) via the same standard API (or documented extensions).
- **SH-REQ-005**: Support adding new OSS models over time (download/register) without client changes.
- **SH-REQ-006**: Allow API requests to specify which model or inference approach to use.
- **SH-REQ-007**: Allow deployment on a home server and cloud with minimal changes.
- **SH-REQ-008**: Provide operational guidance for installing, running, and updating models.
- **SH-REQ-009**: Provide observability (logs, metrics) for usage and failures.
- **SH-REQ-010**: Manage local storage for large models (capacity awareness, cleanup, and caching).
- **SH-REQ-011**: Handle long-running model downloads and provide status/progress feedback.
- **SH-REQ-012**: Require authentication and authorization for access to the standard API, with support for multiple standard auth options.
- **SH-REQ-013**: Provide an endpoint to list available models and their capabilities.
- **SH-REQ-014**: Support streaming responses for text generation (SSE).
- **SH-REQ-015**: Provide artifact storage for large outputs (images, 3D) with downloadable URLs.
- **SH-REQ-016**: Automatically discover locally installed models in storage so they appear in the model catalog.
- **SH-REQ-017**: Provide a clear, queryable description of request parameters and model-specific guidance for API consumers.
- **SH-REQ-018**: Support chat/session management for multi-turn interactions across text, image, and 3D modalities.
- **SH-REQ-019**: Allow clients to create, list, update, and close sessions, including resetting or branching a session when needed.
- **SH-REQ-020**: Support both backend-managed session state and client-supplied state (tokens/variables) for iterative generation workflows.
- **SH-REQ-021**: Provide client libraries (Python and Dart/Flutter) to call the API endpoints with typed requests/responses.
- **SH-REQ-022**: Ensure each client library offers ergonomic session helpers for multi-turn workflows.
- **SH-REQ-023**: Provide a cross-platform frontend UI for text, image, and 3D model interaction.
- **SH-REQ-024**: Allow users to select a model and modality from the UI.
- **SH-REQ-025**: Provide a dynamic settings pane/drawer that renders model-specific parameters from the schema.
- **SH-REQ-026**: Provide a chat-like interface for text models with streaming responses.
- **SH-REQ-027**: Provide modality-specific interfaces for image and 3D generation (gallery/preview, download).
- **SH-REQ-054**: Allow users to attach images to prompts (upload, paste, URL) for models that support image input.
- **SH-REQ-028**: Allow the frontend to be hosted separately from the backend (web app + API base URL config).
- **SH-REQ-029**: Support creation of chats/sessions in the UI with maintained context per user.
- **SH-REQ-030**: Maintain a persistent model registry (internal and external models) including supported parameters.
- **SH-REQ-031**: Allow users to supply and manage their own commercial provider API keys.
- **SH-REQ-032**: Allow users to create and manage API keys for OSS model access.
- **SH-REQ-033**: Provide user authentication (login/logout) with invite-only registration.
- **SH-REQ-034**: Provide user profiles with preferences (preferred models, UI defaults).
- **SH-REQ-035**: Allow users to create private API tokens for the LLM API.
- **SH-REQ-036**: Enrich model registry entries with Hugging Face docs and parameter usage guidance when available.
- **SH-REQ-037**: Allow users to auto-switch UI layout based on modality/device or lock a preferred UI.
- **SH-REQ-038**: Download models in the background with status and avoid duplicate downloads.
- **SH-REQ-039**: Manage model lifecycle (load/unload) with a default model always in memory.
- **SH-REQ-040**: Pre-load models before requests to avoid cold-start latency.
- **SH-REQ-041**: Queue requests when inference resources are busy with position feedback.
- **SH-REQ-042**: Cancel in-flight generation requests.
- **SH-REQ-043**: Regenerate/retry responses with same or modified parameters.
- **SH-REQ-044**: Allow users to choose (via API or frontend) whether to fall back to a default model while the requested model is loading, or to wait for the requested model.
- **SH-REQ-045**: Ensure client applications and SDKs use the exact backend API endpoints and request schemas (no contract drift).
- **SH-REQ-046**: Maintain a clear, up-to-date API endpoint reference for consumers.
- **SH-REQ-047**: Use a shared Dart client library in the frontend to avoid duplicated SDK logic.
- **SH-REQ-048**: Provide a UI workflow to search Hugging Face and download/register new models, with text search for large catalogs.
- **SH-REQ-049**: Allow users to manage commercial provider credentials with support for non-API-key auth methods.
- **SH-REQ-050**: Allow users to manage and switch sessions from a left-pane sessions list (no separate sessions page).
- **SH-REQ-051**: Allow users to name sessions.
- **SH-REQ-052**: Track timestamps for prompts/commands/messages in sessions.
- **SH-REQ-053**: Provide a settings UI action to test API connectivity and show a green check on success.

## Non-Functional Requirements (Stakeholder)
- **SH-NFR-001**: Secure handling of API keys/secrets for commercial providers.
- **SH-NFR-002**: Reliable request handling with clear error reporting.
- **SH-NFR-003**: Reasonable latency for local and remote inference (targets TBD).
- **SH-NFR-004**: Maintainability and extensibility for adding new providers/models.
- **SH-NFR-005**: Usable developer experience (clear docs, consistent request/response format).
- **SH-NFR-006**: Safe and predictable disk usage on hosts with limited storage.
- **SH-NFR-007**: Secure transport for API traffic (TLS where applicable).
- **SH-NFR-008**: Support optional rate limiting for resource protection (future scope).
- **SH-NFR-009**: Cross-platform UI support (web + mobile) with responsive layouts.
- **SH-NFR-010**: UI responsiveness for model selection and parameter updates (<100ms).
- **SH-NFR-011**: Accessibility support (WCAG AA where applicable).
- **SH-NFR-012**: Secure storage and isolation of per-user credentials and API keys.
- **SH-NFR-013**: Access control must enforce invite-only registration and authenticated API usage.

## Constraints and Assumptions
- Local inference hardware may be limited; support must scale down to CPU-only where possible.
- Commercial API usage depends on external provider availability and pricing.
- SQLite is the initial persistence layer for model registry and user keys.
- Future migration target: cloud database (Supabase) when scaling beyond local usage.

## In-Scope / Out-of-Scope
**In-Scope**
- Standard API design and backend adapters
- Local model hosting guidance and infrastructure setup
- Cloud and home-server deployment instructions
- Cross-platform frontend UI for interacting with models

**Out-of-Scope**
- Creating or training new foundation models from scratch

## Key Workflows (3–5)
1. Configure a commercial provider and call the standard API.
2. Configure and run a local OSS LLM and call the standard API.
3. Switch the backend for the same client request with no code changes.
4. Run an image or 3D model generation request through the same API pattern.
5. Deploy the service on a home server and in the cloud.
6. Install a local model file and have it automatically appear in the model catalog.
7. Query API documentation to learn supported parameters and how to pass them.
8. Start a session, send multiple related requests, then close or reset the session.
9. Use a client library to call endpoints without hand-crafting HTTP requests.
10. Select a model in the UI, configure parameters, and generate outputs.
11. Use a settings drawer to adjust model parameters dynamically.
12. Run the web UI hosted separately from the API backend.
13. Create a new chat session, continue context across turns, and switch sessions.
14. Manage personal API keys for commercial providers and OSS access.
15. Register via invite, log in, set preferences, and use personalized model defaults.
16. Create and revoke private API tokens for direct API access.
17. Register a model and see usage guidance and parameters from Hugging Face.
18. Auto-switch UI layouts by modality/device, or lock a preferred layout.
19. Start a model download without blocking the UI or API and see download status.
20. Pre-load a model before making requests to ensure fast response.
21. Cancel a long-running request from the UI.
22. Regenerate a response with modified parameters.
23. Choose to use a fallback model while the preferred model is loading, or wait for the preferred model.

## Edge Cases / Risks
- Local model performance insufficient for real-time use.
- API differences across providers cause feature gaps.
- GPU availability differs between home and cloud environments.

## Success Criteria (Measurable)
- Client can switch providers with no changes to request schema.
- At least one commercial and one local OSS model are successfully invoked through the API.
- Deployment works on both home server and cloud with documented steps.
- Installed local models appear in the catalog without manual registration.
- API consumers can retrieve parameter documentation from the service.
- Multi-turn requests within a session produce coherent, stateful behavior across calls.
- Clients can start and end sessions and see them reflected in session listings.
- Developers can integrate the API via the client libraries with minimal boilerplate in Python and Dart/Flutter.
- Users can interact with models through the UI with dynamic parameter controls.
- Users can create and switch chat sessions with maintained context.
- The system tracks models and parameter schemas persistently.
- Users can authenticate and manage profile preferences.
- Users can create private API tokens for the LLM API.
- Model entries include usage docs and parameter guidance when available.
- UI adapts to modality/device with user override.
- Model downloads run in the background with status and reuse.
- Default model is always loaded and available for immediate use.
- Users can pre-load models and see loading status.
- Requests queue when resources are busy with position feedback.
- Users can cancel in-flight requests.
- Users can regenerate responses with modified parameters.
- Users can choose (via API or UI) to use a fallback model while the preferred model loads, or to wait.
- Users can add/register models from the UI by searching Hugging Face and filtering large lists.
- Users can manage commercial provider credentials, including non-API-key auth types.
- Users can manage and switch sessions from the left-pane sessions list.
- Users can name sessions and see those names in lists.
- Messages include timestamps for prompts/commands/responses.
- Users can test API connectivity from settings and receive a green check on success.

## Decisions (Resolved Open Questions)
- **API shape**: Custom schema (not strictly OpenAI-compatible), but similar patterns.
- **Streaming responses**: Yes, support SSE for text streaming (WebSocket optional/future).
- **OSS model priority**: Text first (e.g., DeepSeek, Llama), then image (Stable Diffusion), then 3D.
- **Latency/throughput**: No hard targets for v1; document observed performance.
- **Hosting approach**: Docker preferred; bare metal supported; Kubernetes optional/future.
- **Authentication**: API key required; OAuth/JWT optional and configurable.

## Definition of Ready / Done
**Ready**
- Stakeholder requirements are outcome-oriented and testable where possible.
- IDs assigned (SH-REQ-###) and NFRs listed.
- Open questions and assumptions documented.

**Done**
- Reviewed and approved by user.
- Traceability matrix created and linked to system requirements.

## Traceability
Stakeholder → System

| Stakeholder Req ID | System Req ID(s) | Notes |
|---|---|---|
| SH-REQ-001 | SYS-REQ-001, SYS-REQ-005 | |
| SH-REQ-002 | SYS-REQ-002, SYS-REQ-006 | |
| SH-REQ-003 | SYS-REQ-003 | |
| SH-REQ-004 | SYS-REQ-004 | |
| SH-REQ-005 | SYS-REQ-010 | |
| SH-REQ-006 | SYS-REQ-011 | |
| SH-REQ-007 | SYS-REQ-009 | |
| SH-REQ-008 | SYS-REQ-009 | |
| SH-REQ-009 | SYS-REQ-008 | |
| SH-REQ-010 | SYS-REQ-012 | |
| SH-REQ-011 | SYS-REQ-013 | |
| SH-REQ-012 | SYS-REQ-014 | |
| SH-REQ-013 | SYS-REQ-015 | |
| SH-REQ-014 | SYS-REQ-017 | Streaming |
| SH-REQ-015 | SYS-REQ-016 | Artifact store |
| SH-REQ-016 | SYS-REQ-018 | Model auto-discovery |
| SH-REQ-017 | SYS-REQ-019 | Parameter documentation |
| SH-REQ-018 | SYS-REQ-020 | Session management |
| SH-REQ-019 | SYS-REQ-021 | Session lifecycle |
| SH-REQ-020 | SYS-REQ-022 | Session state handoff |
| SH-REQ-021 | SYS-REQ-023 | Client library |
| SH-REQ-022 | SYS-REQ-024 | Session helpers |
| SH-REQ-023 | SYS-REQ-025 | Cross-platform UI |
| SH-REQ-024 | SYS-REQ-026 | Model selection UI |
| SH-REQ-025 | SYS-REQ-027 | Dynamic parameters |
| SH-REQ-026 | SYS-REQ-028 | Chat UI |
| SH-REQ-027 | SYS-REQ-029, SYS-REQ-030 | Image/3D UI |
| SH-REQ-054 | SYS-REQ-070 | Image input attachments |
| SH-REQ-028 | SYS-REQ-031 | Separate hosting |
| SH-REQ-029 | SYS-REQ-032 | Frontend sessions |
| SH-REQ-030 | SYS-REQ-033, SYS-REQ-034 | Model registry |
| SH-REQ-031 | SYS-REQ-035 | User provider keys |
| SH-REQ-032 | SYS-REQ-036 | User OSS keys |
| SH-REQ-033 | SYS-REQ-037 | Auth & invite-only registration |
| SH-REQ-034 | SYS-REQ-038 | User profiles/preferences |
| SH-REQ-035 | SYS-REQ-039 | User API tokens |
| SH-REQ-036 | SYS-REQ-040 | Model documentation enrichment |
| SH-REQ-037 | SYS-REQ-041 | UI auto-switch/lock |
| SH-REQ-038 | SYS-REQ-042, SYS-REQ-043, SYS-REQ-044 | Background downloads, status, dedupe |
| SH-REQ-039 | SYS-REQ-045, SYS-REQ-050, SYS-REQ-051, SYS-REQ-052 | Model lifecycle |
| SH-REQ-040 | SYS-REQ-049 | Pre-load models |
| SH-REQ-041 | SYS-REQ-046 | Request queueing |
| SH-REQ-042 | SYS-REQ-047 | Request cancellation |
| SH-REQ-043 | SYS-REQ-048 | Regenerate/retry |
| SH-REQ-044 | SYS-REQ-052, SYS-REQ-053 | Fallback configuration |
| SH-REQ-045 | SYS-REQ-055, SYS-REQ-056, SYS-REQ-057, SYS-REQ-058, SYS-REQ-059, SYS-REQ-060 | Endpoint alignment |
| SH-REQ-046 | SYS-REQ-061 | API endpoint reference |
| SH-REQ-047 | SYS-REQ-062 | Shared Dart client usage |
| SH-REQ-048 | SYS-REQ-063 | Add model workflow + search/filter |
| SH-REQ-049 | SYS-REQ-064 | Provider credentials (non-API-key) |
| SH-REQ-050 | SYS-REQ-065 | Sessions list contract |
| SH-REQ-051 | SYS-REQ-066 | Session naming |
| SH-REQ-052 | SYS-REQ-067 | Session/message timestamps |
| SH-REQ-053 | SYS-REQ-068 | API connection test |
| SH-REQ-024 | SYS-REQ-026 | Model selection UI |
| SH-REQ-025 | SYS-REQ-027 | Dynamic parameters |
| SH-REQ-026 | SYS-REQ-028 | Chat UI |
| SH-REQ-027 | SYS-REQ-029, SYS-REQ-030 | Image/3D UI |
| SH-REQ-028 | SYS-REQ-031 | Separate hosting |
| SH-REQ-029 | SYS-REQ-032 | Frontend sessions |
| SH-REQ-030 | SYS-REQ-033, SYS-REQ-034 | Model registry |
| SH-REQ-031 | SYS-REQ-035 | User provider keys |
| SH-REQ-032 | SYS-REQ-036 | User OSS keys |
| SH-REQ-033 | SYS-REQ-037 | Authentication & invite-only registration |
| SH-REQ-034 | SYS-REQ-038 | User profiles & preferences |
| SH-REQ-035 | SYS-REQ-039 | User API tokens |
| SH-REQ-036 | SYS-REQ-040 | Model documentation enrichment |
| SH-REQ-037 | SYS-REQ-041 | UI auto-switch/lock |
| SH-REQ-038 | SYS-REQ-042, SYS-REQ-043, SYS-REQ-044 | Background downloads, status, dedupe |
