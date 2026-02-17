# Test User Credentials

For testing the LLM API gateway, a test user has been created in the database.

## Credentials
- **Email**: test@example.com
- **Password**: testpass123

## Usage
1. Start the backend server: `uvicorn llm_api.main:app --port 8080`
2. Use the Flutter frontend or API to login with these credentials.
3. For API login, POST to `/v1/users/login` with the email and password.

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
- This user is created directly in the SQLite database for testing purposes.
- The password is hashed using PBKDF2 with SHA256.
- Invite requirement has been disabled in the config for testing.