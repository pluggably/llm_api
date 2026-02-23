"""Database connection and session management."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from llm_api.config import get_settings
from llm_api.db.models import Base


_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def _apply_postgres_schema(engine: Engine, schema: str) -> None:
    """Set search_path for every PostgreSQL connection.

    Some poolers may ignore startup `options` in the URL, so enforce it
    explicitly on connect.
    """
    normalized = (schema or "").strip()
    if not normalized:
        return

    @event.listens_for(engine, "connect")
    def _set_search_path(dbapi_connection, connection_record):  # type: ignore[no-redef]
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f'SET search_path TO "{normalized}", public')
        finally:
            cursor.close()


def get_database_url() -> str:
    """Get the database URL from settings."""
    settings = get_settings()
    if settings.database_url:
        return _normalize_database_url(settings.database_url, settings.database_schema)
    db_path = Path(settings.model_path) / "llm_api.db"
    return f"sqlite:///{db_path}"


def _normalize_database_url(raw_url: str, schema: str | None = None) -> str:
    """Normalize DB URL for SQLAlchemy/driver compatibility."""
    normalized = raw_url.strip()
    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql+psycopg://", 1)
    elif normalized.startswith("postgresql://") and "+" not in normalized.split("://", 1)[0]:
        normalized = normalized.replace("postgresql://", "postgresql+psycopg://", 1)

    if normalized.startswith("postgresql+psycopg://"):
        parsed = urlparse(normalized)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.setdefault("sslmode", "require")
        if schema:
            options = query.get("options", "")
            search_path_token = f"-c search_path={schema}"
            if search_path_token not in options:
                options = f"{options} {search_path_token}".strip()
                query["options"] = options
        parsed = parsed._replace(query=urlencode(query))
        normalized = urlunparse(parsed)

    return normalized


def init_db() -> None:
    """Initialize the database engine and create tables."""
    global _engine, _SessionLocal
    
    database_url = get_database_url()
    settings = get_settings()
    is_sqlite = database_url.startswith("sqlite")
    _engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if is_sqlite else {},
        pool_pre_ping=True,
        echo=False,
    )

    if not is_sqlite and settings.database_schema:
        _apply_postgres_schema(_engine, settings.database_schema)

        # Ensure target schema exists before create_all(). If the schema does
        # not exist, PostgreSQL will place new tables in `public` instead.
        with _engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.database_schema}"'))

    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    # Create all tables
    Base.metadata.create_all(bind=_engine)

    if is_sqlite:
        _ensure_session_title_column(_engine)
        _ensure_model_image_columns(_engine)
        _ensure_provider_keys_columns(_engine)
        _ensure_default_models_table(_engine)


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


def _ensure_model_image_columns(engine: Engine) -> None:
    """Ensure models table has image constraint columns (CR-002)."""
    new_cols = {
        "image_input_max_edge": "INTEGER",
        "image_input_max_pixels": "INTEGER",
        "image_input_formats": "JSON",
    }
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(models)"))
            existing = {row[1] for row in result}
            for col, typ in new_cols.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE models ADD COLUMN {col} {typ}"))
            conn.commit()
    except Exception:
        pass


def _ensure_provider_keys_columns(engine: Engine) -> None:
    """Ensure provider_keys table has credential_type column."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(provider_keys)"))
            existing = {row[1] for row in result}
            if "credential_type" not in existing:
                conn.execute(
                    text("ALTER TABLE provider_keys ADD COLUMN credential_type VARCHAR(50) NOT NULL DEFAULT 'api_key'")
                )
                conn.commit()
    except Exception:
        pass


def _ensure_default_models_table(engine: Engine) -> None:
    """Ensure default_models table exists for default model overrides."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(default_models)"))
            columns = {row[1] for row in result}
            if not columns:
                conn.execute(
                    text(
                        "CREATE TABLE default_models ("
                        "modality VARCHAR(20) PRIMARY KEY, "
                        "model_id VARCHAR(255), "
                        "updated_at DATETIME"
                        ")"
                    )
                )
                conn.commit()
    except Exception:
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
