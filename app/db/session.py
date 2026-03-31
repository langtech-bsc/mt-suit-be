"""Database engine and session management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _engine_factory() -> AsyncEngine:
    database_settings = settings.database
    return create_async_engine(
        database_settings.async_url,
        echo=database_settings.echo,
        pool_size=database_settings.pool_size,
        max_overflow=database_settings.max_overflow,
    )


def _session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False)


engine = _engine_factory()
AsyncSessionFactory = _session_factory(engine)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Provide a managed lifespan for async database sessions."""

    session = AsyncSessionFactory()
    try:
        yield session
    except Exception:
        if session.in_transaction():
            await session.rollback()
        raise
    finally:
        await session.close()


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an async SQLAlchemy session."""

    async with session_scope() as session:
        yield session


__all__ = [
    "engine",
    "AsyncSessionFactory",
    "session_scope",
    "get_session",
]
