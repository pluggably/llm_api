"""User authentication and profile API endpoints."""
from __future__ import annotations

import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from llm_api.api.schemas import (
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


@users_router.post("/register")
async def register(request: UserRegisterRequest) -> JSONResponse:
    """Register a new user (requires invite token if configured)."""
    user_service = get_user_service()
    
    result = user_service.register(
        email=request.email,
        password=request.password,
        invite_token=request.invite_token,
        display_name=request.display_name,
    )
    
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Registration failed. Invalid invite token or email already exists.",
        )
    
    return JSONResponse(jsonable_encoder(result), status_code=201)


@users_router.post("/login")
async def login(request: UserLoginRequest) -> JSONResponse:
    """Authenticate and get an access token."""
    user_service = get_user_service()
    
    user = user_service.authenticate(request.email, request.password)
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


@users_router.get("/me", dependencies=[Depends(require_api_key)])
async def get_profile() -> JSONResponse:
    """Get current user profile."""
    # TODO: Get user from auth context
    # For now, return a placeholder
    raise HTTPException(status_code=501, detail="User context not implemented")


@users_router.patch("/me", dependencies=[Depends(require_api_key)])
async def update_profile(request: UpdateProfileRequest) -> JSONResponse:
    """Update current user profile."""
    # TODO: Get user from auth context
    raise HTTPException(status_code=501, detail="User context not implemented")


@users_router.post("/tokens", dependencies=[Depends(require_api_key)])
async def create_token(request: CreateTokenRequest) -> JSONResponse:
    """Create a new API token."""
    # TODO: Get user from auth context
    user_service = get_user_service()
    
    # Placeholder user_id
    user_id = "placeholder"
    
    result = user_service.create_api_token(
        user_id=user_id,
        name=request.name,
        scopes=request.scopes,
        expires_days=request.expires_days,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create token")
    
    token, token_info = result
    return JSONResponse(
        jsonable_encoder(TokenCreatedResponse(token=token, info=TokenInfo(**token_info))),
        status_code=201,
    )


@users_router.get("/tokens", dependencies=[Depends(require_api_key)])
async def list_tokens() -> JSONResponse:
    """List API tokens for the current user."""
    # TODO: Get user from auth context
    user_service = get_user_service()
    user_id = "placeholder"
    
    tokens = user_service.list_api_tokens(user_id)
    return JSONResponse(jsonable_encoder(tokens))


@users_router.delete("/tokens/{token_id}", dependencies=[Depends(require_api_key)])
async def revoke_token(token_id: str) -> JSONResponse:
    """Revoke an API token."""
    # TODO: Get user from auth context
    user_service = get_user_service()
    user_id = "placeholder"
    
    if not user_service.revoke_api_token(user_id, token_id):
        raise HTTPException(status_code=404, detail="Token not found")
    
    return JSONResponse({"revoked": True})


@users_router.post("/provider-keys", dependencies=[Depends(require_api_key)])
async def set_provider_key(request: ProviderKeyRequest) -> JSONResponse:
    """Set a provider API key."""
    # TODO: Get user from auth context
    user_service = get_user_service()
    user_id = "placeholder"

    payload = {}
    if request.credential_type == "api_key":
        if not request.api_key:
            raise HTTPException(status_code=400, detail="api_key is required")
        payload = {"api_key": request.api_key}
    elif request.credential_type == "endpoint_key":
        if not request.api_key or not request.endpoint:
            raise HTTPException(status_code=400, detail="api_key and endpoint are required")
        payload = {"api_key": request.api_key, "endpoint": request.endpoint}
    elif request.credential_type == "oauth_token":
        if not request.oauth_token:
            raise HTTPException(status_code=400, detail="oauth_token is required")
        payload = {"oauth_token": request.oauth_token}
    elif request.credential_type == "service_account":
        if not request.service_account_json:
            raise HTTPException(
                status_code=400,
                detail="service_account_json is required",
            )
        payload = {"service_account_json": request.service_account_json}

    result = user_service.set_provider_key(
        user_id,
        request.provider,
        request.credential_type,
        payload,
    )
    return JSONResponse(jsonable_encoder(result), status_code=201)


@users_router.get("/provider-keys", dependencies=[Depends(require_api_key)])
async def list_provider_keys() -> JSONResponse:
    """List provider keys for the current user."""
    # TODO: Get user from auth context
    user_service = get_user_service()
    user_id = "placeholder"
    
    keys = user_service.list_provider_keys(user_id)
    return JSONResponse(jsonable_encoder(keys))


@users_router.delete("/provider-keys/{provider}", dependencies=[Depends(require_api_key)])
async def delete_provider_key(provider: str) -> JSONResponse:
    """Delete a provider API key."""
    # TODO: Get user from auth context
    user_service = get_user_service()
    user_id = "placeholder"
    
    if not user_service.delete_provider_key(user_id, provider):
        raise HTTPException(status_code=404, detail="Provider key not found")
    
    return JSONResponse({"deleted": True})


@users_router.post("/invites", dependencies=[Depends(require_api_key)])
async def create_invite() -> JSONResponse:
    """Create an invite token (admin only)."""
    # TODO: Check admin permission
    user_service = get_user_service()
    
    token = user_service.create_invite()
    return JSONResponse({"invite_token": token}, status_code=201)
