from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import get_settings


def _connect_args(url: str) -> dict:
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


_settings = get_settings()
engine = create_engine(_settings.database_url, connect_args=_connect_args(_settings.database_url))

# Read-only engine for AI-generated SQL. In production, point DATABASE_URL_READONLY at a
# Postgres role granted SELECT only. Locally it falls back to the main DB, and the
# SQL guard in services/claude.py still refuses anything but a single SELECT.
readonly_engine = (
    create_engine(_settings.database_url_readonly, connect_args=_connect_args(_settings.database_url_readonly))
    if _settings.database_url_readonly
    else engine
)


def init_db() -> None:
    from . import models  # noqa: F401  (registers tables)

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
