"""Database engine, session and portable column types.

Production runs on PostgreSQL 16 (JSONB, pg_trgm, unaccent). Local development and the
test-suite run on SQLite through the same models: the types below pick the native
PostgreSQL type when available and a portable equivalent otherwise.
"""

from __future__ import annotations

import uuid
import warnings
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, MetaData, TypeDecorator, Uuid, event, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SAWarning
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings
from app.core.ids import uuid7

# SQLite stores Numeric as text/float; precision is fine for INR with 2 decimals.
warnings.filterwarnings("ignore", category=SAWarning, message=".*Decimal objects natively.*")

JSONType = JSON().with_variant(JSONB(), "postgresql")


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetimes on every backend (SQLite drops tzinfo)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        value = value.astimezone(UTC)
        if dialect.name == "sqlite":
            return value.replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def utcnow() -> datetime:
    return datetime.now(UTC)


NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map = {datetime: UTCDateTime(), dict: JSONType, list: JSONType}


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow, server_default=func.now()
    )


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _make_engine(url: str, null_pool: bool = False) -> AsyncEngine:
    kwargs: dict = {"pool_pre_ping": True}
    if null_pool:
        from sqlalchemy.pool import NullPool

        kwargs = {"poolclass": NullPool}
    if url.startswith("sqlite"):
        kwargs = {"connect_args": {"timeout": 30}}
    engine = create_async_engine(url, **kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(engine.sync_engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _):  # noqa: ANN001
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=30000")
            cur.close()

    return engine


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is None:
        _engine = _make_engine(get_settings().database_url)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def configure_engine(url: str, null_pool: bool = False) -> AsyncEngine:
    """Point the app at a database (tests; Celery tasks use a NullPool per event loop)."""
    global _engine, _sessionmaker
    _engine = _make_engine(url, null_pool)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def sessionmaker() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def get_db() -> AsyncIterator[AsyncSession]:
    async with sessionmaker()() as session:
        yield session


def is_postgres(session_or_engine) -> bool:  # noqa: ANN001
    bind = session_or_engine.get_bind() if isinstance(session_or_engine, AsyncSession) else session_or_engine
    return bind.dialect.name == "postgresql"
