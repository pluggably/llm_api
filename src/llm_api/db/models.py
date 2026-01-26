"""SQLAlchemy models for Pluggably LLM API Gateway."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class ModelRecord(Base):
    """Persisted model registry entry."""
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False, default="latest")
    modality: Mapped[str] = mapped_column(String(20), nullable=False)  # text, image, 3d
    provider: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="available")
    local_path: Mapped[Optional[str]] = mapped_column(String(1024))
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Source info
    source_type: Mapped[Optional[str]] = mapped_column(String(50))  # huggingface, url, local
    source_uri: Mapped[Optional[str]] = mapped_column(String(1024))
    
    # Capabilities
    max_context_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_formats: Mapped[Optional[List[str]]] = mapped_column(JSON)
    hardware_requirements: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text)
    documentation: Mapped[Optional[str]] = mapped_column(Text)  # HuggingFace model card content
    parameter_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Runtime state (not persisted across restarts, updated in memory)
    runtime_status: Mapped[str] = mapped_column(String(50), default="unloaded")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Fallback configuration
    fallback_model_id: Mapped[Optional[str]] = mapped_column(String(255), ForeignKey("models.id"))
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    
    __table_args__ = (
        Index("ix_models_modality", "modality"),
        Index("ix_models_provider", "provider"),
        Index("ix_models_status", "status"),
    )


class UserRecord(Base):
    """User account."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Profile
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    preferred_model: Mapped[Optional[str]] = mapped_column(String(255))
    preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    api_tokens: Mapped[List["UserTokenRecord"]] = relationship("UserTokenRecord", back_populates="user", cascade="all, delete-orphan")
    provider_keys: Mapped[List["ProviderKeyRecord"]] = relationship("ProviderKeyRecord", back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[List["SessionRecord"]] = relationship("SessionRecord", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_users_email", "email"),
    )


class UserTokenRecord(Base):
    """User-created API tokens."""
    __tablename__ = "user_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # Stored hashed
    scopes: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    user: Mapped["UserRecord"] = relationship("UserRecord", back_populates="api_tokens")
    
    __table_args__ = (
        Index("ix_user_tokens_hash", "token_hash"),
    )


class ProviderKeyRecord(Base):
    """User-provided API keys for commercial providers."""
    __tablename__ = "provider_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)  # openai, anthropic, etc.
    credential_type: Mapped[str] = mapped_column(String(50), nullable=False, default="api_key")
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted payload at rest
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user: Mapped["UserRecord"] = relationship("UserRecord", back_populates="provider_keys")
    
    __table_args__ = (
        Index("ix_provider_keys_user_provider", "user_id", "provider"),
    )


class InviteTokenRecord(Base):
    """Invite tokens for registration."""
    __tablename__ = "invite_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))
    used_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))
    
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class SessionRecord(Base):
    """Chat/generation sessions."""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active, closed
    
    # State tokens for iterative workflows
    state_tokens: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    user: Mapped[Optional["UserRecord"]] = relationship("UserRecord", back_populates="sessions")
    messages: Mapped[List["SessionMessageRecord"]] = relationship("SessionMessageRecord", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_status", "status"),
    )


class SessionMessageRecord(Base):
    """Individual messages within a session."""
    __tablename__ = "session_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)  # Order within session
    
    modality: Mapped[str] = mapped_column(String(20), nullable=False)  # text, image, 3d
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    state_tokens: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    session: Mapped["SessionRecord"] = relationship("SessionRecord", back_populates="messages")
    
    __table_args__ = (
        Index("ix_session_messages_session_seq", "session_id", "sequence"),
    )


class RequestRecord(Base):
    """Tracking for in-flight and completed requests."""
    __tablename__ = "requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))
    session_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("sessions.id"))
    model_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    queue_position: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Request data
    modality: Mapped[Optional[str]] = mapped_column(String(20))
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Response data
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timing
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    __table_args__ = (
        Index("ix_requests_status", "status"),
        Index("ix_requests_user_id", "user_id"),
    )


class DownloadJobRecord(Base):
    """Model download jobs."""
    __tablename__ = "download_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[Optional[str]] = mapped_column(Text)
    
    # Source
    source_type: Mapped[Optional[str]] = mapped_column(String(50))
    source_uri: Mapped[Optional[str]] = mapped_column(String(1024))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    __table_args__ = (
        Index("ix_download_jobs_status", "status"),
        Index("ix_download_jobs_model_id", "model_id"),
    )
