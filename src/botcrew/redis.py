import redis.asyncio as aioredis


async def init_redis(redis_url: str) -> aioredis.Redis:
    """Create and return an async Redis client, verifying connectivity with a ping."""
    client = aioredis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    # Verify connection
    await client.ping()
    return client


async def close_redis(client: aioredis.Redis) -> None:
    """Close the async Redis client connection."""
    await client.aclose()
