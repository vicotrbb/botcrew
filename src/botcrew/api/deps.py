"""Shared FastAPI dependencies for database sessions and Redis client injection."""

from collections.abc import AsyncGenerator

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session from the app-level session factory.

    The session factory is stored on ``request.app.state.session_factory``
    by the application lifespan. The session auto-closes when the request ends.
    """
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


async def get_redis(request: Request) -> Redis:
    """Return the async Redis client stored on app state.

    The Redis client is initialized during the application lifespan
    and stored on ``request.app.state.redis``.
    """
    return request.app.state.redis
