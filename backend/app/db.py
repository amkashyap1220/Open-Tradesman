from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import get_settings


def normalize_url(url: str) -> str:
    """Point Postgres URLs at the psycopg 3 driver we install.

    Neon/Supabase hand out postgres:// or postgresql:// URLs; SQLAlchemy reads the first as
    invalid and the second as psycopg2 (not installed).
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def make_engine(url: str):
    url = normalize_url(url)
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    # Hosted Postgres drops idle connections (pre_ping replaces dead ones), and its
    # transaction-mode poolers break server-side prepared statements (prepare_threshold=None).
    return create_engine(url, pool_pre_ping=True, pool_recycle=300, connect_args={"prepare_threshold": None})


_settings = get_settings()
engine = make_engine(_settings.database_url)

# Read-only engine for AI-generated SQL. In production, point DATABASE_URL_READONLY at a
# Postgres role granted SELECT only. Locally it falls back to the main DB, and the
# SQL guard in services/claude.py still refuses anything but a single SELECT.
readonly_engine = make_engine(_settings.database_url_readonly) if _settings.database_url_readonly else engine


def init_db() -> None:
    """Create missing tables. DDL goes over the direct connection when one is set:
    Neon's pooler (PgBouncer, transaction mode) is for app traffic, not schema changes."""
    from . import models  # noqa: F401  (registers tables)

    if _settings.database_url_unpooled:
        ddl_engine = make_engine(_settings.database_url_unpooled)
        try:
            SQLModel.metadata.create_all(ddl_engine)
        finally:
            ddl_engine.dispose()
    else:
        SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
