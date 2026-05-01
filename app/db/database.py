"""Database engine and session helpers."""

from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.models import Base


def normalize_database_url(database_url: str) -> str:
    """Return a SQLAlchemy-compatible database URL."""
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith(("http://", "https://")):
        raise ValueError(
            "INSFORGE_DATABASE_URL must be a SQLAlchemy database URL, not an HTTP API URL. "
            "Use a postgresql:// URL for InsForge Postgres access."
        )
    return database_url


def create_app_engine(database_url: Optional[str] = None) -> Engine:
    """Create a SQLAlchemy engine for SQLite or Postgres."""
    url = normalize_database_url(database_url or settings.effective_database_url)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker[Session]] = None


def get_engine() -> Engine:
    """Return the configured application engine."""
    global _engine
    if _engine is None:
        _engine = create_app_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the configured session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _session_factory


def init_db() -> None:
    """Create all MVP database tables."""
    Base.metadata.create_all(bind=get_engine())


@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a database session and close it after use."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
