"""Reusable dependencies for database access."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import session_scope


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession for FastAPI dependency injection."""

    async with session_scope() as session:
        yield session
