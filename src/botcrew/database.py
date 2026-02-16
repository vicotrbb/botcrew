from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


async def init_db(database_url: str) -> AsyncEngine:
    """Create and return an async SQLAlchemy engine."""
    engine = create_async_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )
    return engine


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create and return an async session factory bound to the given engine."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def close_db(engine: AsyncEngine) -> None:
    """Dispose of the async engine and release all connections."""
    await engine.dispose()
