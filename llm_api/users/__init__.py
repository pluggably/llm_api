"""User authentication and authorization module."""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet

from llm_api.config import get_settings
from llm_api.db.database import get_db_session
from llm_api.db.models import (
    InviteTokenRecord,
    ProviderKeyRecord,
    UserRecord,
    UserTokenRecord,
)


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash a password with salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    )
    return hashed.hex(), salt


def _verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verify a password against its hash."""
    computed, _ = _hash_password(password, salt)
    return secrets.compare_digest(computed, password_hash)


def _hash_token(token: str) -> str:
    """Hash a token for storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# Module-level cache for the generated fallback key (only for dev/testing)
_fallback_encryption_key: bytes | None = None


def _get_encryption_key() -> bytes:
    """Get a stable encryption key for provider keys.

    Priority:
    1. ``LLM_API_ENCRYPTION_KEY`` env/config (production)
    2. A key persisted to ``<model_path>/.llm_api_enc.key`` (auto-generated on
       first run, then reused — survives restarts without extra config)
    """
    import base64
    settings = get_settings()
    if settings.encryption_key:
        raw = hashlib.sha256(settings.encryption_key.encode()).digest()
        return base64.urlsafe_b64encode(raw)

    # Persist a generated key alongside the database so it survives restarts.
    key_file = Path(settings.model_path) / ".llm_api_enc.key"
    try:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        if key_file.exists():
            stored = key_file.read_bytes().strip()
            if len(stored) == 44:  # Fernet key is always 44 url-safe base64 chars
                return stored
        # Generate and persist a new key
        new_key = Fernet.generate_key()
        key_file.write_bytes(new_key)
        # Restrict permissions on Unix
        try:
            import os
            os.chmod(key_file, 0o600)
        except Exception:
            pass
        logging.getLogger(__name__).warning(
            "No encryption_key configured — generated and persisted a key at %s. "
            "Set LLM_API_ENCRYPTION_KEY for production deployments.",
            key_file,
        )
        return new_key
    except Exception:
        pass  # Fall through to in-memory fallback

    global _fallback_encryption_key
    if _fallback_encryption_key is None:
        logging.getLogger(__name__).warning(
            "Could not persist encryption key — using ephemeral key. "
            "Provider credentials will be lost on restart. "
            "Set LLM_API_ENCRYPTION_KEY for production."
        )
        _fallback_encryption_key = Fernet.generate_key()
    return _fallback_encryption_key


def _encrypt_key(plaintext: str) -> str:
    """Encrypt a provider API key."""
    key = _get_encryption_key()
    f = Fernet(key)
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def _decrypt_key(ciphertext: str) -> str:
    """Decrypt a provider API key."""
    key = _get_encryption_key()
    f = Fernet(key)
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def _mask_provider_payload(payload: Dict[str, Any], credential_type: str) -> Optional[str]:
    secret = payload.get("api_key") or payload.get("oauth_token")
    if isinstance(secret, str) and len(secret) >= 6:
        return f"{secret[:3]}...{secret[-3:]}"
    if isinstance(secret, str):
        return "***"
    if credential_type == "endpoint_key":
        endpoint = payload.get("endpoint")
        return f"{endpoint} (key hidden)" if endpoint else "(key hidden)"
    if credential_type == "service_account":
        return "service_account_json"
    return None


class UserService:
    """Service for user management."""

    def ensure_user(
        self,
        email: str,
        password: str,
        *,
        display_name: Optional[str] = None,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """Create or update a user with the provided credentials/role."""
        password_hash, salt = _hash_password(password)
        combined_hash = f"{salt}:{password_hash}"

        with get_db_session() as db:
            user = db.query(UserRecord).filter(UserRecord.email == email).first()
            if user:
                user.password_hash = combined_hash
                user.is_admin = bool(is_admin)
                user.is_active = True
                if display_name is not None:
                    user.display_name = display_name
                db.flush()
                return {
                    "id": user.id,
                    "username": user.email,
                    "email": user.email,
                    "display_name": user.display_name,
                    "is_admin": user.is_admin,
                }

            user_id = str(uuid.uuid4())
            user = UserRecord(
                id=user_id,
                email=email,
                password_hash=combined_hash,
                is_admin=bool(is_admin),
                display_name=display_name or email.split("@")[0],
            )
            db.add(user)
            db.flush()
            return {
                "id": user_id,
                "username": email,
                "email": email,
                "display_name": user.display_name,
                "is_admin": user.is_admin,
            }
    
    def create_invite(self, created_by: Optional[str] = None, expires_days: int = 7) -> str:
        """Create an invite token."""
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        
        invite = InviteTokenRecord(
            id=str(uuid.uuid4()),
            token_hash=token_hash,
            created_by=created_by,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days),
        )
        
        with get_db_session() as db:
            db.add(invite)
        
        return token
    
    def validate_invite(self, token: str) -> bool:
        """Validate an invite token."""
        token_hash = _hash_token(token)
        
        with get_db_session() as db:
            invite = db.query(InviteTokenRecord).filter(
                InviteTokenRecord.token_hash == token_hash,
                InviteTokenRecord.is_used == False,
            ).first()
            
            if not invite:
                return False
            
            if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
                return False
            
            return True
    
    def register(
        self,
        email: str,
        password: str,
        invite_token: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Register a new user."""
        settings = get_settings()
        
        # Check invite requirement
        if settings.invite_required:
            if not invite_token or not self.validate_invite(invite_token):
                return None
        
        # Hash password
        password_hash, salt = _hash_password(password)
        combined_hash = f"{salt}:{password_hash}"
        
        user_id = str(uuid.uuid4())
        user = UserRecord(
            id=user_id,
            email=email,
            password_hash=combined_hash,
            display_name=display_name or email.split("@")[0],
        )
        
        with get_db_session() as db:
            # Check if email exists
            existing = db.query(UserRecord).filter(UserRecord.email == email).first()
            if existing:
                return None
            
            db.add(user)
            
            # Mark invite as used
            if invite_token:
                token_hash = _hash_token(invite_token)
                invite = db.query(InviteTokenRecord).filter(
                    InviteTokenRecord.token_hash == token_hash
                ).first()
                if invite:
                    invite.is_used = True
                    invite.used_by = user_id
        
        return {
            "id": user_id,
            "username": email,
            "email": email,
            "display_name": user.display_name,
        }
    
    def authenticate(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user."""
        with get_db_session() as db:
            user = db.query(UserRecord).filter(
                UserRecord.email == email,
                UserRecord.is_active == True,
            ).first()
            
            if not user:
                return None
            
            # Verify password
            parts = user.password_hash.split(":", 1)
            if len(parts) != 2:
                return None
            
            salt, password_hash = parts
            if not _verify_password(password, password_hash, salt):
                return None
            
            # Update last login
            user.last_login_at = datetime.now(timezone.utc)
            
            return {
                "id": user.id,
                "username": user.email,
                "email": user.email,
                "display_name": user.display_name,
                "is_admin": user.is_admin,
            }

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change password for an existing user after verifying current password."""
        if len(new_password) < 12:
            return False

        with get_db_session() as db:
            user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
            if not user or not user.is_active:
                return False

            parts = user.password_hash.split(":", 1)
            if len(parts) != 2:
                return False

            salt, existing_hash = parts
            if not _verify_password(current_password, existing_hash, salt):
                return False

            password_hash, new_salt = _hash_password(new_password)
            user.password_hash = f"{new_salt}:{password_hash}"
            db.flush()
            return True
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user by ID."""
        with get_db_session() as db:
            user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
            if not user:
                return None
            
            return {
                "id": user.id,
                "username": user.email,
                "email": user.email,
                "display_name": user.display_name,
                "is_admin": user.is_admin,
                "preferred_model": user.preferred_model,
                "preferences": user.preferences or {},
            }
    
    def update_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        preferred_model: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update user profile."""
        with get_db_session() as db:
            user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
            if not user:
                return None
            
            if display_name is not None:
                user.display_name = display_name
            if preferred_model is not None:
                user.preferred_model = preferred_model
            if preferences is not None:
                user.preferences = preferences
            
            return self.get_user(user_id)
    
    def create_api_token(
        self,
        user_id: str,
        name: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        expires_days: Optional[int] = None,
    ) -> Optional[tuple[str, Dict[str, Any]]]:
        """Create an API token for a user. Returns (token, token_info)."""
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        
        token_record = UserTokenRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            token_hash=token_hash,
            scopes=scopes or [],
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days) if expires_days else None,
        )
        
        with get_db_session() as db:
            db.add(token_record)
            db.flush()
            db.refresh(token_record)
            token_info = {
                "id": token_record.id,
                "name": name,
                "scopes": scopes or [],
                "created_at": token_record.created_at.isoformat(),
                "expires_at": token_record.expires_at.isoformat() if token_record.expires_at else None,
            }
        
        return token, token_info
    
    def list_api_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        """List API tokens for a user (without revealing token values)."""
        with get_db_session() as db:
            tokens = db.query(UserTokenRecord).filter(
                UserTokenRecord.user_id == user_id,
                UserTokenRecord.is_active == True,
            ).all()
            
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "scopes": t.scopes or [],
                    "created_at": t.created_at.isoformat(),
                    "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
                    "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                }
                for t in tokens
            ]
    
    def revoke_api_token(self, user_id: str, token_id: str) -> bool:
        """Revoke an API token."""
        with get_db_session() as db:
            token = db.query(UserTokenRecord).filter(
                UserTokenRecord.id == token_id,
                UserTokenRecord.user_id == user_id,
            ).first()
            
            if not token:
                return False
            
            token.is_active = False
            return True
    
    def validate_api_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate an API token and return user info."""
        token_hash = _hash_token(token)
        
        with get_db_session() as db:
            token_record = db.query(UserTokenRecord).filter(
                UserTokenRecord.token_hash == token_hash,
                UserTokenRecord.is_active == True,
            ).first()
            
            if not token_record:
                return None
            
            if token_record.expires_at:
                expires_at = token_record.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < datetime.now(timezone.utc):
                    return None
            
            # Update last used
            token_record.last_used_at = datetime.now(timezone.utc)
            
            user = db.query(UserRecord).filter(UserRecord.id == token_record.user_id).first()
            if not user or not user.is_active:
                return None
            
            return {
                "user_id": user.id,
                "username": user.email,
                "email": user.email,
                "scopes": token_record.scopes or [],
            }
    
    def set_provider_key(
        self,
        user_id: str,
        provider: str,
        credential_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Set a provider credential for a user."""
        logger = logging.getLogger(__name__)
        logger.debug(
            "Setting provider key",
            extra={"provider": provider, "credential_type": credential_type, "user_id": user_id},
        )
        encrypted = _encrypt_key(json.dumps(payload))
        
        with get_db_session() as db:
            existing = db.query(ProviderKeyRecord).filter(
                ProviderKeyRecord.user_id == user_id,
                ProviderKeyRecord.provider == provider,
            ).first()
            
            if existing:
                existing.encrypted_key = encrypted
                existing.credential_type = credential_type
                existing.is_active = True
                key_id = existing.id
                created_at = existing.created_at
            else:
                key_record = ProviderKeyRecord(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    provider=provider,
                    credential_type=credential_type,
                    encrypted_key=encrypted,
                )
                db.add(key_record)
                db.flush()
                key_id = key_record.id
                created_at = key_record.created_at

        masked_key = _mask_provider_payload(payload, credential_type)
        return {
            "id": key_id,
            "provider": provider,
            "credential_type": credential_type,
            "masked_key": masked_key,
            "created_at": created_at.isoformat() if created_at else None,
        }
    
    def get_provider_key(self, user_id: str, provider: str) -> Optional[str]:
        """Get a decrypted provider API key for a user."""
        with get_db_session() as db:
            key_record = db.query(ProviderKeyRecord).filter(
                ProviderKeyRecord.user_id == user_id,
                ProviderKeyRecord.provider == provider,
                ProviderKeyRecord.is_active == True,
            ).first()
            
            if not key_record:
                return None
            
            try:
                payload = json.loads(_decrypt_key(key_record.encrypted_key))
            except Exception:
                return None
            return payload.get("api_key")

    def get_provider_credentials(self, user_id: str, provider: str) -> Optional[Dict[str, Any]]:
        """Get decrypted provider credentials payload for a user."""
        with get_db_session() as db:
            key_record = db.query(ProviderKeyRecord).filter(
                ProviderKeyRecord.user_id == user_id,
                ProviderKeyRecord.provider == provider,
                ProviderKeyRecord.is_active == True,
            ).first()

            if not key_record:
                return None

            try:
                payload = json.loads(_decrypt_key(key_record.encrypted_key))
            except Exception:
                return None
            payload["credential_type"] = key_record.credential_type
            return payload
    
    def list_provider_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """List provider credentials for a user (without revealing secret values)."""
        with get_db_session() as db:
            keys = db.query(ProviderKeyRecord).filter(
                ProviderKeyRecord.user_id == user_id,
                ProviderKeyRecord.is_active == True,
            ).all()
            
            results: List[Dict[str, Any]] = []
            for k in keys:
                masked_key = None
                try:
                    payload = json.loads(_decrypt_key(k.encrypted_key))
                    masked_key = _mask_provider_payload(payload, k.credential_type)
                except Exception:
                    masked_key = None
                results.append(
                    {
                        "id": k.id,
                        "provider": k.provider,
                        "credential_type": k.credential_type,
                        "masked_key": masked_key,
                        "created_at": k.created_at.isoformat(),
                    },
                )
            return results
    
    def delete_provider_key(self, user_id: str, provider: str) -> bool:
        """Delete a provider API key."""
        with get_db_session() as db:
            key_record = db.query(ProviderKeyRecord).filter(
                ProviderKeyRecord.user_id == user_id,
                ProviderKeyRecord.provider == provider,
            ).first()
            
            if not key_record:
                return False
            
            key_record.is_active = False
            return True


# Global instance
_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """Get the global user service instance."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
