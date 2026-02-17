"""Shared FastAPI dependencies for database sessions, Redis, pod manager, and communication services."""

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.services.channel_service import ChannelService
from botcrew.services.communication import CommunicationService, NativeTransport
from botcrew.services.message_service import MessageService
from botcrew.services.pod_manager import PodManager


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


async def get_pod_manager(request: Request) -> PodManager:
    """Return the PodManager instance stored on app state.

    The PodManager is initialized during the application lifespan
    and stored on ``request.app.state.pod_manager``.
    """
    return request.app.state.pod_manager


async def get_channel_service(
    db: AsyncSession = Depends(get_db),
) -> ChannelService:
    """Provide a ChannelService instance with the current DB session."""
    return ChannelService(db)


async def get_message_service(
    db: AsyncSession = Depends(get_db),
) -> MessageService:
    """Provide a MessageService instance with the current DB session."""
    return MessageService(db)


async def get_communication_service(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CommunicationService:
    """Provide a CommunicationService with MessageService, ChannelService, and NativeTransport.

    NativeTransport receives the app's Redis connection (request.app.state.redis)
    for direct pub/sub publishing to channel subscribers. This is the same Redis
    connection used elsewhere -- publishing is a regular command, not blocking,
    so sharing is safe.
    """
    return CommunicationService(
        message_service=MessageService(db),
        channel_service=ChannelService(db),
        transport=NativeTransport(redis=request.app.state.redis),
    )
