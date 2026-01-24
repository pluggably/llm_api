# ADR 002: Auto-Discover Local Models and Provide Schema Endpoint

**Date**: January 24, 2026
**Status**: Accepted (Change Request CR-2026-01-24-01)

## Context
Operators install local model files directly into the model storage path. API consumers need a reliable way to discover available models and understand request parameters without out-of-band documentation. The existing model catalog depends on explicit registration and does not document parameters beyond OpenAPI.

## Decision
1. Add startup-time auto-discovery of local model files (e.g., `.gguf`) in the configured model storage path, registering them in the model catalog with size, version/quantization, and local path metadata.
2. Add a read-only schema endpoint that returns request parameter documentation (defaults, ranges, examples) and model selection guidance, aligned with OpenAPI.

## Consequences
- **Pros**:
  - Local model availability becomes visible without manual registration.
  - API consumers can self-serve parameter guidance programmatically.
- **Cons**:
  - Startup time increases due to filesystem scan.
  - Requires clear rules to avoid overwriting explicitly registered models.

## Alternatives Considered
- **Manual registry updates only**: rejected due to operator burden and inconsistency.
- **OpenAPI-only documentation**: insufficient for runtime parameter guidance and examples.

## Related Requirements
- SYS-REQ-018, SYS-REQ-019, INT-REQ-005, DATA-REQ-007
