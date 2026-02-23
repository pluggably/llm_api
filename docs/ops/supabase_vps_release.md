# Supabase + VPS Release Runbook

This is the first-phase migration path from local SQLite to Supabase Postgres and a production VPS deployment.

## 1) Get connection credentials from Supabase

Supabase now exposes database connection strings from the **Connect** button in your project dashboard.

1. Open your Supabase project dashboard.
2. Click **Connect** (top area of the project UI).
3. Copy either:
  - **Direct connection** (best for persistent VPS runtime when IPv6 is available), or
  - **Session pooler** (good fallback for IPv4-only VPS networks).
4. Ensure your DB password is set/reset in Supabase and substitute it in the URL.

Use the connection URL in `LLM_API_DATABASE_URL`.

### Dashboard click-map (current UI)

If you cannot find old "Project Settings → Database" links, use this path:

1. Supabase Dashboard → **Projects** → select your project.
2. In the project header/top bar, click **Connect**.
3. In Connect modal, pick connection type:
  - **Direct connection** (persistent VPS, IPv6-capable), or
  - **Session pooler** (IPv4-compatible fallback).
4. Copy the URI and replace `<PASSWORD>` with your DB password.
5. If needed, reset DB password from **Project Settings → Configuration/Data API & Database credentials** (label may vary by UI version), then paste the new password into the URI.

Example:

```bash
export LLM_API_DATABASE_URL='postgresql+psycopg://postgres:<PASSWORD>@db.<PROJECT>.supabase.co:5432/postgres?sslmode=require'
```

## 1.5) Isolate this app with a dedicated schema (recommended)

If you use one Supabase project for multiple apps, isolate each app by schema to avoid table-name collisions (`users`, `models`, `sessions`, etc).

### Option A: SQL Editor (fastest)

Run in Supabase SQL Editor:

```sql
create schema if not exists llm_api;
```

Then set:

```bash
LLM_API_DATABASE_SCHEMA=llm_api
```

This API automatically appends `search_path=llm_api` to PostgreSQL URLs when `LLM_API_DATABASE_SCHEMA` is set.

### Option B: Supabase CLI-managed migration

```bash
brew install supabase/tap/supabase
supabase login
supabase link --project-ref <your-project-ref>
supabase migration new create_llm_api_schema
```

Put this SQL in the created migration file:

```sql
create schema if not exists llm_api;
```

Then apply:

```bash
supabase db push
```

## 2) Required production env vars

At minimum:

```bash
LLM_API_API_KEY=<strong-random-key>
LLM_API_DATABASE_URL=<supabase-postgres-url>
LLM_API_DATABASE_SCHEMA=llm_api
LLM_API_ENCRYPTION_KEY=<strong-random-key>
LLM_API_INVITE_REQUIRED=true
LLM_API_LOG_LEVEL=INFO
```

Important:
- `LLM_API_ENCRYPTION_KEY` must be stable across restarts.
- Keep provider API keys in user-scoped provider key storage, not plaintext env vars.

## 2.5) Local vs VPS env examples

You can run the same codebase in both places; only env values change.

### VPS (recommended: Direct connection)

```bash
LLM_API_DATABASE_URL='postgresql+psycopg://postgres:<PASSWORD>@db.<PROJECT>.supabase.co:5432/postgres?sslmode=require'
LLM_API_DATABASE_SCHEMA=llm_api
LLM_API_API_KEY=<strong-random-key>
LLM_API_ENCRYPTION_KEY=<strong-random-key>
```

### Local dev (if Direct works)

```bash
LLM_API_DATABASE_URL='postgresql+psycopg://postgres:<PASSWORD>@db.<PROJECT>.supabase.co:5432/postgres?sslmode=require'
LLM_API_DATABASE_SCHEMA=llm_api
LLM_API_API_KEY=dev-local-key
LLM_API_ENCRYPTION_KEY=<same-stable-key-or-dev-key>
```

### Local dev fallback (if Direct fails due to IPv6)

Use Supabase **Session pooler** URI from **Connect**:

```bash
LLM_API_DATABASE_URL='postgresql+psycopg://postgres.<PROJECT_REF>:<PASSWORD>@aws-0-<REGION>.pooler.supabase.com:5432/postgres?sslmode=require'
LLM_API_DATABASE_SCHEMA=llm_api
LLM_API_API_KEY=dev-local-key
LLM_API_ENCRYPTION_KEY=<same-stable-key-or-dev-key>
```

### Quick connectivity check

If direct URI fails locally, you likely need pooler/IPv4 path:

```bash
python - <<'PY'
import socket
host = 'db.<PROJECT>.supabase.co'
print(socket.getaddrinfo(host, 5432, socket.AF_UNSPEC, socket.SOCK_STREAM))
PY
```

If you only get IPv6 entries and your local network cannot route IPv6, use Session pooler for local development.

## 3) One-time data migration (SQLite -> Supabase)

Run from your repo root:

```bash
python scripts/migrate_sqlite_to_postgres.py \
  --source "sqlite:////absolute/path/to/models/llm_api.db" \
  --target "$LLM_API_DATABASE_URL" \
  --truncate-target
```

Notes:
- `--truncate-target` clears matching target tables before copying.
- Run this first in staging and validate sessions/users/models before prod cutover.
- This migration copies `users`, `user_tokens`, `provider_keys`, and `invite_tokens`.
- If `LLM_API_DATABASE_SCHEMA` is set, run migration with a target URL that includes the same schema search path (or export the schema in the environment before running the app and migration tooling).

If this is a fresh environment, create admin users explicitly:

```bash
python scripts/create_user.py --username hassan --password '<strong-password>' --admin
python scripts/create_user.py --username ben --password '<strong-password>' --admin
```

## 4) VPS deploy baseline

Use your existing `uvicorn` + `systemd` + `nginx` flow, but ensure the service loads:

- `LLM_API_DATABASE_URL`
- `LLM_API_ENCRYPTION_KEY`
- `LLM_API_API_KEY`

Recommended uvicorn settings:

```bash
uvicorn llm_api.main:app --host 0.0.0.0 --port 8080 --workers 2
```

## 5) Pre-release validation checklist

- Health endpoint returns OK (`/health`)
- Login/register works
- Provider key CRUD works
- Session create/list/get works
- Text generation works with at least one provider
- Model listing and defaults work

## 6) Cutover plan

1. Freeze writes on old instance.
2. Run final migration copy.
3. Restart API on VPS with Supabase env.
4. Smoke test critical endpoints.
5. Monitor logs and error rates for 30–60 minutes.

## 7) Rollback plan

If issues occur:
- Revert VPS env to SQLite mode by unsetting `LLM_API_DATABASE_URL`.
- Restart service.
- Re-enable old instance traffic.
