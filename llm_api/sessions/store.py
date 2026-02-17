from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select

from llm_api.api.schemas import Session, SessionMessageResponse, SessionSummary
from llm_api.config import get_settings
from llm_api.db.database import get_db_session
from llm_api.db.models import SessionMessageRecord as DbSessionMessageRecord
from llm_api.db.models import SessionRecord as DbSessionRecord


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
    title: Optional[str] = None
    last_used_at: Optional[datetime] = None
    messages: List[SessionMessage] = field(default_factory=list)
    state_tokens: Optional[Dict[str, Any]] = None
    message_count: int = 0

    def touch(self) -> None:
        self.last_used_at = datetime.now(timezone.utc)

    def to_summary(self) -> SessionSummary:
        return SessionSummary(
            id=self.id,
            title=self.title,
            created_at=self.created_at,
            last_used_at=self.last_used_at,
            message_count=self.message_count,
        )

    def to_public(self, include_messages: bool = False) -> Session:
        messages = None
        if include_messages:
            messages = self.to_messages()
        return Session(
            id=self.id,
            status=self.status,
            title=self.title,
            created_at=self.created_at,
            last_used_at=self.last_used_at,
            message_count=self.message_count,
            messages=messages,
        )

    def to_messages(self) -> List[SessionMessageResponse]:
        output: List[SessionMessageResponse] = []
        for message in self.messages:
            user_content = message.input.get("prompt") if message.input else None
            if user_content:
                output.append(
                    SessionMessageResponse(
                        id=message.id,
                        role="user",
                        content=str(user_content),
                        created_at=message.created_at,
                    ),
                )
            assistant_content = None
            if message.output:
                assistant_content = message.output.get("text")
            if assistant_content:
                output.append(
                    SessionMessageResponse(
                        id=message.id,
                        role="assistant",
                        content=str(assistant_content),
                        created_at=message.created_at,
                    ),
                )
        return output


class SessionStore:
    def __init__(self) -> None:
        pass

    def _cleanup_expired(self) -> None:
        settings = get_settings()
        retention_minutes = getattr(settings, "session_retention_minutes", 0)
        if retention_minutes <= 0:
            return
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=retention_minutes)
        with get_db_session() as db:
            expired = (
                select(DbSessionRecord)
                .where(
                    func.coalesce(DbSessionRecord.last_used_at, DbSessionRecord.created_at)
                    < cutoff,
                )
            )
            records = db.execute(expired).scalars().all()
            for record in records:
                db.delete(record)

    def create_session(self, title: Optional[str] = None) -> SessionRecord:
        now = datetime.now(timezone.utc)
        session_id = str(uuid.uuid4())
        record = DbSessionRecord(
            id=session_id,
            status="active",
            created_at=now,
            last_used_at=now,
            title=title,
        )
        with get_db_session() as db:
            db.add(record)
            return SessionRecord(
                id=session_id,
                status="active",
                created_at=now,
                last_used_at=now,
                title=title,
            )

    def list_sessions(self) -> List[SessionSummary]:
        self._cleanup_expired()
        with get_db_session() as db:
            query = select(DbSessionRecord).order_by(
                DbSessionRecord.last_used_at.desc().nulls_last(),
                DbSessionRecord.created_at.desc(),
            )
            records = db.execute(query).scalars().all()
            result = []
            for record in records:
                msg_count_query = select(func.count(DbSessionMessageRecord.id)).where(
                    DbSessionMessageRecord.session_id == record.id,
                )
                msg_count = db.execute(msg_count_query).scalar() or 0
                result.append(
                    SessionSummary(
                        id=record.id,
                        title=record.title,
                        created_at=record.created_at,
                        last_used_at=record.last_used_at,
                        message_count=msg_count,
                    )
                )
            return result

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        self._cleanup_expired()
        with get_db_session() as db:
            record = db.get(DbSessionRecord, session_id)
            if not record:
                return None
            record.last_used_at = datetime.now(timezone.utc)
            db.add(record)

            messages_query = (
                select(DbSessionMessageRecord)
                .where(DbSessionMessageRecord.session_id == session_id)
                .order_by(DbSessionMessageRecord.sequence.asc())
            )
            messages = db.execute(messages_query).scalars().all()

            return SessionRecord(
                id=record.id,
                status=record.status,
                created_at=record.created_at,
                last_used_at=record.last_used_at,
                title=record.title,
                state_tokens=record.state_tokens,
                message_count=len(messages),
                messages=[
                    SessionMessage(
                        id=message.id,
                        modality=message.modality,
                        input=message.input_data or {},
                        output=message.output_data or {},
                        state_tokens=message.state_tokens,
                        created_at=message.created_at,
                    )
                    for message in messages
                ],
            )

    def reset_session(self, session_id: str) -> Optional[SessionRecord]:
        with get_db_session() as db:
            record = db.get(DbSessionRecord, session_id)
            if not record:
                return None
            db.execute(
                delete(DbSessionMessageRecord).where(
                    DbSessionMessageRecord.session_id == session_id,
                ),
            )
            record.state_tokens = None
            record.last_used_at = datetime.now(timezone.utc)
            db.add(record)
            return SessionRecord(
                id=record.id,
                status=record.status,
                created_at=record.created_at,
                last_used_at=record.last_used_at,
                title=record.title,
                state_tokens=None,
                messages=[],
            )

    def update_session(self, session_id: str, title: Optional[str] = None) -> Optional[SessionRecord]:
        with get_db_session() as db:
            record = db.get(DbSessionRecord, session_id)
            if not record:
                return None
            if title is not None:
                record.title = title
            record.last_used_at = datetime.now(timezone.utc)
            db.add(record)
            return SessionRecord(
                id=record.id,
                status=record.status,
                created_at=record.created_at,
                last_used_at=record.last_used_at,
                title=record.title,
                state_tokens=record.state_tokens,
                messages=[],
            )

    def close_session(self, session_id: str) -> Optional[SessionRecord]:
        with get_db_session() as db:
            record = db.get(DbSessionRecord, session_id)
            if not record:
                return None
            record.status = "closed"
            record.last_used_at = datetime.now(timezone.utc)
            db.add(record)
            return SessionRecord(
                id=record.id,
                status=record.status,
                created_at=record.created_at,
                last_used_at=record.last_used_at,
                title=record.title,
                state_tokens=record.state_tokens,
                messages=[],
            )

    def append_message(
        self,
        session_id: str,
        modality: str,
        input_payload: Dict[str, Any],
        output_payload: Dict[str, Any],
        state_tokens: Optional[Dict[str, Any]],
    ) -> Optional[SessionRecord]:
        with get_db_session() as db:
            record = db.get(DbSessionRecord, session_id)
            if not record:
                return None
            next_seq_query = select(func.max(DbSessionMessageRecord.sequence)).where(
                DbSessionMessageRecord.session_id == session_id,
            )
            next_seq = (db.execute(next_seq_query).scalar() or 0) + 1

            # Auto-name: set title from first user prompt when untitled
            if record.title is None and next_seq == 1:
                prompt = input_payload.get("prompt", "") or ""
                if prompt:
                    truncated = prompt[:50].strip()
                    if len(prompt) > 50:
                        truncated = f"{prompt[:47].strip()}..."
                    record.title = truncated

            message = DbSessionMessageRecord(
                id=str(uuid.uuid4()),
                session_id=session_id,
                sequence=next_seq,
                modality=modality,
                input_data=input_payload,
                output_data=output_payload,
                state_tokens=state_tokens,
                created_at=datetime.now(timezone.utc),
            )
            db.add(message)
            record.state_tokens = state_tokens
            record.last_used_at = datetime.now(timezone.utc)
            db.add(record)
            return SessionRecord(
                id=record.id,
                status=record.status,
                created_at=record.created_at,
                last_used_at=record.last_used_at,
                title=record.title,
                state_tokens=record.state_tokens,
                message_count=next_seq,
                messages=[],
            )


_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
