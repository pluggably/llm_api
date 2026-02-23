# ADR 007: Provider Discovery, Credits, and Vendor Selection

**Date**: 2026-02-19
**Status**: Proposed

## Context
We need to discover accessible commercial models per user based on stored provider credentials and surface credit/usage availability. The backend must support requests that specify a provider/vendor instead of a model ID, allowing free-tier fallback when premium credits are exhausted. This capability should primarily live in the backend API; frontend support is secondary.

## Decision
1. Implement a **Provider Discovery** subsystem that queries provider APIs (OpenAI, Anthropic, Google, Azure, xAI; DeepSeek when configured) using user credentials to list accessible models and retrieve credit/usage status where available.
2. Cache discovery results per user/provider with TTL and rate limits to avoid throttling.
3. Add an optional request field `provider` to indicate vendor preference when `model` is omitted.
4. When premium credits are exhausted or unknown, the router will select a free-tier fallback model and include a **fallback indicator** in responses.

## Consequences
- API responses must include selection metadata (selected model/provider, fallback indicators) and optional credit status.
- Provider discovery adds external API dependencies and requires robust caching and error handling.
- Logging must never include secrets or raw credential payloads.
- OpenAPI and client SDKs will require updates once implementation begins.
