# Test User Credentials

Users are not bootstrapped automatically.
Create test/admin users explicitly with the helper script.

## Credentials
- **Username**: test
- **Password**: choose a strong password

## Admin Accounts

Create admins explicitly:

```bash
python scripts/create_user.py --username hassan --password '<strong-password>' --admin
python scripts/create_user.py --username ben --password '<strong-password>' --admin
python scripts/create_user.py --username test --password '<strong-password>'
```

Use unique passwords per environment.

## Usage
1. Start the backend server: `uvicorn llm_api.main:app --port 8080`
2. Create users via `scripts/create_user.py`.
3. Use the Flutter frontend or API to login with these credentials.
4. For API login, POST to `/v1/users/login` with the username (or legacy email) and password.

## API Endpoint Corrections (Jan 26, 2026)
The frontend SDK has been updated to match the actual backend API endpoints:

### Auth
- ✅ `/v1/users/register` (was `/v1/auth/register`)
- ✅ `/v1/users/login` (was `/v1/auth/login`)
- ✅ No logout endpoint (local token clear only)

### Generation
- ✅ `/v1/generate` (was `/v1/completions`)
- Request schema: `{model, modality, input: {prompt}, parameters}`

### Lifecycle
- ✅ `/v1/models/{model_id}/status` (was `/v1/models/status`)
- ✅ `/v1/models/{model_id}/load` (was `/v1/models/load`)
- ✅ `/v1/models/{model_id}/unload` (was `/v1/models/unload`)

### Requests
- ✅ `/v1/requests/{request_id}/status` (was `/v1/request/{request_id}/status`)
- ✅ `/v1/requests/{request_id}/cancel` (was `/v1/request/{request_id}/cancel`)

### Sessions
- ✅ `/v1/sessions/{session_id}` PUT endpoint added for updates

### User Management
- ✅ `/v1/users/tokens` (no `/me` prefix)
- ✅ `/v1/users/provider-keys` (no `/me` prefix)
- ✅ Provider keys deleted by provider name, not ID

## Notes
- The password is hashed using PBKDF2 with SHA256.
- Registration is invite-gated when `LLM_API_INVITE_REQUIRED=true`.
- Authenticated users can change their password via `POST /v1/users/change-password`.