# ADR-005: Database-Backed Model Registry

## Status
Accepted

## Date
2026-01-26

## Context

The model registry was originally implemented with two persistence options:
1. **In-memory only**: Model metadata lost on server restart
2. **JSON file** (`registry.json`): Optional persistence via `LLM_API_PERSIST_STATE=true`

This caused problems when downloading models from HuggingFace:
- Downloaded files have different names than their model IDs (e.g., `sd_xl_base_1.0.safetensors` vs `stabilityai/stable-diffusion-xl-base-1.0`)
- Without persistence enabled, the mapping between model ID and local file was lost on restart
- Auto-scan of local files couldn't recover the original HuggingFace repo ID
- Users encountered "Model not found" errors for models that were actually downloaded

The system already had a SQLite database with a `models` table that was defined but not used by the registry.

## Decision

Migrate the `ModelRegistry` class from JSON file persistence to SQLite database persistence using the existing `models` table.

### Key Changes

1. **Registry Store** (`llm_api/registry/store.py`):
   - Rewritten to use SQLAlchemy with `get_db_session()`
   - All CRUD operations now persist to `models` table
   - Added `get_model_by_local_path()` method for file-based lookups
   - Auto-scan still discovers local files but stores metadata in database

2. **Downloader** (`llm_api/jobs/downloader.py`):
   - Removed `.meta.json` file creation
   - Stores HuggingFace repo ID in `source_type` and `source_uri` columns
   - Model metadata persisted via database, not sidecar files

3. **Database Schema** (already existed in `models` table):
   - `id`: Model ID (e.g., `stabilityai/stable-diffusion-xl-base-1.0`)
   - `local_path`: Filename of downloaded file (e.g., `sd_xl_base_1.0.safetensors`)
   - `source_type`: `huggingface`, `url`, or `local`
   - `source_uri`: Original source (HuggingFace repo ID or URL)

## Consequences

### Positive
- Model metadata persists across server restarts by default
- No separate `LLM_API_PERSIST_STATE` setting needed for model registry
- HuggingFace repo IDs properly preserved and mapped to local files
- Consistent with other persisted data (users, sessions, provider keys)
- Single source of truth for model metadata

### Negative
- Slight overhead for database operations (mitigated by optional caching)
- Migration required for existing deployments using JSON persistence

### Neutral
- `LLM_API_PERSIST_STATE` setting no longer affects model registry (may still be used for other features)
- `registry.json` file no longer used and can be deleted

## Related
- Database schema: `llm_api/db/models.py` (`ModelRecord` class)
- API schemas: `llm_api/api/schemas.py` (`ModelInfo`, `ModelSource`)
