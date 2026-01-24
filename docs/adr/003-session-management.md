# ADR 003: Session Management for Multi-Turn Requests

**Date**: January 24, 2026
**Status**: Accepted (Change Request CR-2026-01-24-02)

## Context
Users need multi-turn interactions across text, image, and 3D generation. The current API is stateless per request, so follow-up prompts or iterative image/3D refinement cannot reuse context.

## Decision
Introduce session management APIs to create, list, reset, and close sessions. Generation requests may reference a `session_id` (or use a session-scoped generation endpoint) to reuse context across calls.
Additionally, support optional client-supplied state tokens for iterative workflows; when sessions are used, the backend stores and returns updated tokens.

## Consequences
- **Pros**:
  - Enables coherent multi-turn interactions.
  - Supports iterative image/3D refinement workflows.
  - Supports stateless clients by allowing explicit token passthrough.
- **Cons**:
  - Requires storage for session state and retention policies.
  - Adds API surface area and lifecycle complexity.

## Alternatives Considered
- Stateless client-managed context: rejected due to inconsistent client implementations.
- Provider-specific session storage: rejected due to portability issues.

## Related Requirements
- SYS-REQ-020, SYS-REQ-021, INT-REQ-006, DATA-REQ-008
