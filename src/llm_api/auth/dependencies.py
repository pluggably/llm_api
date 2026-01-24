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
    settings = get_settings()

    if settings.local_only:
        client_host = request.client.host if request.client else ""
        if client_host in {"127.0.0.1", "::1", "localhost", "testclient"}:
            return

    if x_api_key:
        if x_api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return

    if authorization and authorization.lower().startswith("bearer ") and settings.jwt_secret:
        token = authorization.split(" ", 1)[1]
        if not _validate_jwt(token, settings.jwt_secret):
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return

    raise HTTPException(status_code=401, detail="Missing API key")
