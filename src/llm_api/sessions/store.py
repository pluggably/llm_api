from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from llm_api.api.schemas import Session
from llm_api.config import get_settings


@dataclass
class SessionMessage:
    id: str
    modality: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    state_tokens: Optional[Dict[str, Any]]
    created_at: datetime


@dataclass
class SessionRecord:
    id: str
    status: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    messages: List[SessionMessage] = field(default_factory=list)
    state_tokens: Optional[Dict[str, Any]] = None

    def touch(self) -> None:
        self.last_used_at = datetime.now(timezone.utc)

    def to_public(self) -> Session:
        return Session(
            id=self.id,
            status=self.status,
            created_at=self.created_at,
            last_used_at=self.last_used_at,
        )


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionRecord] = {}

    def _cleanup_expired(self) -> None:
        settings = get_settings()
        retention_minutes = getattr(settings, "session_retention_minutes", 0)
        if retention_minutes <= 0:
            return
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=retention_minutes)
        for session_id, session in list(self._sessions.items()):
            last_used = session.last_used_at or session.created_at
            if last_used < cutoff:
                self._sessions.pop(session_id, None)

    def create_session(self) -> SessionRecord:
        now = datetime.now(timezone.utc)
        session_id = str(uuid.uuid4())
        session = SessionRecord(
            id=session_id,
            status="active",
            created_at=now,
            last_used_at=now,
        )
        self._sessions[session_id] = session
        return session

    def list_sessions(self) -> List[Session]:
        self._cleanup_expired()
        return [session.to_public() for session in self._sessions.values()]

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        self._cleanup_expired()
        session = self._sessions.get(session_id)
        if session:
            session.touch()
        return session

    def reset_session(self, session_id: str) -> Optional[SessionRecord]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        session.messages = []
        session.state_tokens = None
        session.touch()
        return session

    def close_session(self, session_id: str) -> Optional[SessionRecord]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        session.status = "closed"
        session.touch()
        return session

    def append_message(
        self,
        session_id: str,
        modality: str,
        input_payload: Dict[str, Any],
        output_payload: Dict[str, Any],
        state_tokens: Optional[Dict[str, Any]],
    ) -> Optional[SessionRecord]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        message = SessionMessage(
            id=str(uuid.uuid4()),
            modality=modality,
            input=input_payload,
            output=output_payload,
            state_tokens=state_tokens,
            created_at=datetime.now(timezone.utc),
        )
        session.messages.append(message)
        session.state_tokens = state_tokens
        session.touch()
        return session


_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
