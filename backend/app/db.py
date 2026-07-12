"""Async database engine, session factory, and schema init.

SQLite via aiosqlite now (`create_all` — no migration tool); a connection-URL swap
moves this to Postgres/asyncpg later. The stored snapshot is disposable — it
repopulates from sources on each poll — so `create_all` is enough.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create tables if absent. Imports models so they register on the metadata."""
    from app import models  # noqa: F401  (registers tables on Base.metadata)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
