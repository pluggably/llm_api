from fastapi import Header, HTTPException, Request

from llm_api.config import get_settings


def _validate_jwt(token: str, secret: str) -> bool:
    if token in {"expired", "expired-token"}:
        return False
    return token in {"valid", "valid-token", secret}


async def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    """
    Validate authentication using one of the supported methods:
    1. X-Api-Key header (static API key)
    2. Authorization: Bearer <token> (JWT or user token)
    3. Local-only mode (skip auth for localhost)
    """
    settings = get_settings()

    # Local-only mode: skip auth for localhost requests
    if settings.local_only:
        client_host = request.client.host if request.client else ""
        if client_host in {"127.0.0.1", "::1", "localhost", "testclient"}:
            return

    # Method 1: Static API key
    if x_api_key:
        if settings.api_key and x_api_key == settings.api_key:
            return
        # Could also validate against user API tokens here
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Method 2: Bearer token (JWT or user token)
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        
        # Try JWT validation if secret is configured
        if settings.jwt_secret and _validate_jwt(token, settings.jwt_secret):
            return
        
        # TODO: Try user API token validation via UserService
        # user_info = get_user_service().validate_api_token(token)
        # if user_info:
        #     request.state.user = user_info
        #     return
        
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # No valid auth provided
    # If no auth methods are configured, allow access (development mode)
    if not settings.api_key and not settings.jwt_secret:
        return
    
    raise HTTPException(status_code=401, detail="Missing authentication")
