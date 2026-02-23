from typing import Any, Dict, Optional

import jwt
from fastapi import Header, HTTPException, Request

from llm_api.config import get_settings
from llm_api.users import get_user_service


def _validate_jwt(token: str, secret: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token. Returns claims dict or None."""
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"])
        return claims
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def _get_user_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """Extract the authenticated user info from request state."""
    return getattr(request.state, "user", None)


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
            if not getattr(request.state, "user", None):
                request.state.user = {
                    "user_id": "dev-user",
                    "username": "dev",
                    "email": "dev@localhost",
                    "scopes": [],
                }
            return

    # Method 1: Static API key
    if x_api_key:
        if settings.api_key and x_api_key == settings.api_key:
            # Set a dev-mode user context so user-scoped endpoints work
            if not getattr(request.state, "user", None):
                request.state.user = {
                    "user_id": "dev-user",
                    "username": "dev",
                    "email": "dev@localhost",
                    "scopes": [],
                }
            return
        # Try user API token validation
        user_info = get_user_service().validate_api_token(x_api_key)
        if user_info:
            request.state.user = user_info
            return
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Method 2: Bearer token (JWT or user token)
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]

        # Try JWT validation if secret is configured
        if settings.jwt_secret:
            claims = _validate_jwt(token, settings.jwt_secret)
            if claims:
                user_id = claims.get("sub")
                if user_id:
                    user_service = get_user_service()
                    user = user_service.get_user(user_id)
                    if user:
                        request.state.user = {
                            "user_id": user["id"],
                            "username": user.get("username", user["email"]),
                            "email": user["email"],
                            "scopes": claims.get("scopes", []),
                        }
                        return
                else:
                    # JWT valid but no sub claim — treat as service token
                    request.state.user = {
                        "user_id": claims.get("sub", "jwt-user"),
                        "username": claims.get("username", claims.get("email", "")),
                        "email": claims.get("email", ""),
                        "scopes": claims.get("scopes", []),
                    }
                    return

        # Try user API token validation via UserService
        user_info = get_user_service().validate_api_token(token)
        if user_info:
            request.state.user = user_info
            return

        raise HTTPException(status_code=401, detail="Invalid or expired token")

    raise HTTPException(status_code=401, detail="Missing authentication")
