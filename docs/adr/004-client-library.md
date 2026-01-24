# ADR 004: Client Library Scope and Language

**Date**: January 24, 2026
**Status**: Accepted (Change Request CR-2026-01-24-03)

## Context
Developers need a typed, ergonomic way to call the API without hand-crafting HTTP requests. A client library should cover the full API surface, including sessions.

## Decision
Create versioned client libraries aligned with the API contract in Python and Dart/Flutter. Each library will include typed models, error mapping, and session helpers.

## Consequences
- **Pros**:
  - Faster integration for developers
  - Fewer client-side errors
- **Cons**:
  - Requires maintenance to stay aligned with API changes

## Alternatives Considered
- Only provide OpenAPI and rely on external generators (less ergonomic)
- Provide snippets only (insufficient for production use)

## Related Requirements
- SYS-REQ-023, SYS-REQ-024, INT-REQ-008, DATA-REQ-010
