"""User authentication and profile API endpoints."""
from __future__ import annotations

import secrets
from typing import Any, Dict, List, Optional

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from llm_api.api.schemas import (
    ChangePasswordRequest,
    CreateTokenRequest,
    ProviderKeyInfo,
    ProviderKeyRequest,
    TokenCreatedResponse,
    TokenInfo,
    UpdateProfileRequest,
    UserLoginRequest,
    UserLoginResponse,
    UserProfile,
    UserRegisterRequest,
)
from llm_api.auth import require_api_key
from llm_api.users import get_user_service


users_router = APIRouter(prefix="/v1/users", tags=["users"])


def _get_current_user_id(request: Request) -> str:
    """Extract authenticated user ID from request, or raise 401."""
    user = getattr(request.state, "user", None)
    if user and isinstance(user, dict):
        uid = user.get("user_id") or user.get("id")
        if uid:
            return uid
    raise HTTPException(
        status_code=401,
        detail="Could not determine authenticated user. Please log in again.",
    )


def _require_admin(request: Request) -> str:
    """Require admin privileges and return current user_id."""
    user_id = _get_current_user_id(request)
    user_service = get_user_service()
    user = user_service.get_user(user_id)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user_id


@users_router.post("/register")
async def register(request: UserRegisterRequest) -> JSONResponse:
    """Register a new user (requires invite token if configured)."""
    user_service = get_user_service()
    
    result = user_service.register(
        email=request.username,
        password=request.password,
        invite_token=request.invite_token,
        display_name=request.display_name,
    )
    
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Registration failed. Invalid invite token or username already exists.",
        )
    
    return JSONResponse(jsonable_encoder(result), status_code=201)


@users_router.post("/login")
async def login(request: UserLoginRequest) -> JSONResponse:
    """Authenticate and get an access token."""
    user_service = get_user_service()
    
    user = user_service.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create a session token
    result = user_service.create_api_token(
        user_id=user["id"],
        name="session",
        expires_days=7,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create session token")
    
    token, token_info = result
    return JSONResponse(jsonable_encoder(UserLoginResponse(token=token, user=user)))


@users_router.get("/me")
async def get_profile(request: Request, _=Depends(require_api_key)) -> JSONResponse:
    """Get current user profile."""
    user_id = _get_current_user_id(request)
    user_service = get_user_service()
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return JSONResponse(jsonable_encoder(UserProfile(**user)))


@users_router.patch("/me")
async def update_profile(
    request: Request,
    body: UpdateProfileRequest,
    _=Depends(require_api_key),
) -> JSONResponse:
    """Update current user profile."""
    user_id = _get_current_user_id(request)
    user_service = get_user_service()
    result = user_service.update_profile(
        user_id=user_id,
        display_name=body.display_name,
        preferred_model=body.preferred_model,
        preferences=body.preferences,
    )
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return JSONResponse(jsonable_encoder(result))


@users_router.post("/change-password")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    _=Depends(require_api_key),
) -> JSONResponse:
    """Change current user's password."""
    user_id = _get_current_user_id(request)
    user_service = get_user_service()
    changed = user_service.change_password(
        user_id=user_id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    if not changed:
        raise HTTPException(
            status_code=400,
            detail="Password change failed. Check current password and password policy.",
        )
    return JSONResponse({"changed": True})


@users_router.post("/tokens")
async def create_token(
    request: Request,
    body: CreateTokenRequest,
    _=Depends(require_api_key),
) -> JSONResponse:
    """Create a new API token."""
    user_id = _get_current_user_id(request)
    user_service = get_user_service()
    
    result = user_service.create_api_token(
        user_id=user_id,
        name=body.name,
        scopes=body.scopes,
        expires_days=body.expires_days,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create token")
    
    token, token_info = result
    return JSONResponse(
        jsonable_encoder(TokenCreatedResponse(token=token, info=TokenInfo(**token_info))),
        status_code=201,
    )


@users_router.get("/tokens")
async def list_tokens(request: Request, _=Depends(require_api_key)) -> JSONResponse:
    """List API tokens for the current user."""
    user_id = _get_current_user_id(request)
    user_service = get_user_service()
    
    tokens = user_service.list_api_tokens(user_id)
    return JSONResponse(jsonable_encoder(tokens))


@users_router.delete("/tokens/{token_id}")
async def revoke_token(
    token_id: str,
    request: Request,
    _=Depends(require_api_key),
) -> JSONResponse:
    """Revoke an API token."""
    user_id = _get_current_user_id(request)
    user_service = get_user_service()
    
    if not user_service.revoke_api_token(user_id, token_id):
        raise HTTPException(status_code=404, detail="Token not found")
    
    return JSONResponse({"revoked": True})


@users_router.post("/provider-keys")
async def set_provider_key(
    request: Request,
    body: ProviderKeyRequest,
    _=Depends(require_api_key),
) -> JSONResponse:
    """Set a provider API key."""
    logger = logging.getLogger(__name__)
    user_id = _get_current_user_id(request)
    user_service = get_user_service()

    logger.debug(
        "Received provider key update",
        extra={"provider": body.provider, "credential_type": body.credential_type, "user_id": user_id},
    )

    payload = {}
    if body.credential_type == "api_key":
        if not body.api_key:
            raise HTTPException(status_code=400, detail="api_key is required")
        payload = {"api_key": body.api_key}
    elif body.credential_type == "endpoint_key":
        if not body.api_key or not body.endpoint:
            raise HTTPException(status_code=400, detail="api_key and endpoint are required")
        payload = {"api_key": body.api_key, "endpoint": body.endpoint}
    elif body.credential_type == "oauth_token":
        if not body.oauth_token:
            raise HTTPException(status_code=400, detail="oauth_token is required")
        payload = {"oauth_token": body.oauth_token}
    elif body.credential_type == "service_account":
        if not body.service_account_json:
            raise HTTPException(
                status_code=400,
                detail="service_account_json is required",
            )
        payload = {"service_account_json": body.service_account_json}

    result = user_service.set_provider_key(
        user_id,
        body.provider,
        body.credential_type,
        payload,
    )
    return JSONResponse(jsonable_encoder(result), status_code=201)


@users_router.get("/provider-keys")
async def list_provider_keys(
    request: Request,
    _=Depends(require_api_key),
) -> JSONResponse:
    """List provider keys for the current user."""
    user_id = _get_current_user_id(request)
    user_service = get_user_service()
    
    keys = user_service.list_provider_keys(user_id)
    return JSONResponse(jsonable_encoder(keys))


@users_router.delete("/provider-keys/{provider}")
async def delete_provider_key(
    provider: str,
    request: Request,
    _=Depends(require_api_key),
) -> JSONResponse:
    """Delete a provider API key."""
    user_id = _get_current_user_id(request)
    user_service = get_user_service()
    
    if not user_service.delete_provider_key(user_id, provider):
        raise HTTPException(status_code=404, detail="Provider key not found")
    
    return JSONResponse({"deleted": True})


@users_router.post("/invites")
async def create_invite(request: Request, _=Depends(require_api_key)) -> JSONResponse:
    """Create an invite token (admin only)."""
    user_id = _require_admin(request)
    user_service = get_user_service()
    
    token = user_service.create_invite(created_by=user_id)
    return JSONResponse({"invite_token": token}, status_code=201)
