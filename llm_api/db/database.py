"""Database connection and session management."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from llm_api.config import get_settings
from llm_api.db.models import Base


_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def get_database_url() -> str:
    """Get the database URL from settings."""
    settings = get_settings()
    db_path = Path(settings.model_path) / "llm_api.db"
    return f"sqlite:///{db_path}"


def init_db() -> None:
    """Initialize the database engine and create tables."""
    global _engine, _SessionLocal
    
    database_url = get_database_url()
    _engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},  # SQLite specific
        echo=False,
    )
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    # Create all tables
    Base.metadata.create_all(bind=_engine)

    _ensure_session_title_column(_engine)


def _ensure_session_title_column(engine: Engine) -> None:
    """Ensure sessions table has a title column for backward compatibility."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(sessions)"))
            columns = {row[1] for row in result}
            if "title" not in columns:
                conn.execute(text("ALTER TABLE sessions ADD COLUMN title VARCHAR(255)"))
                conn.commit()
    except Exception:
        # Best-effort migration for SQLite; ignore if not applicable
        pass


def close_db() -> None:
    """Close the database connection."""
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None


def get_db() -> Generator[Session, None, None]:
    """Get a database session."""
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    
    assert _SessionLocal is not None  # For type checker
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    
    assert _SessionLocal is not None  # For type checker
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
