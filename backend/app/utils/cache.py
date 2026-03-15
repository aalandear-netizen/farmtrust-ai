"""Redis caching utilities."""

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """Return the shared Redis client, or None if unavailable."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    """Get a cached value, returning None on miss or if Redis is unavailable."""
    try:
        client = await get_redis()
        value = await client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except (RedisConnectionError, Exception) as exc:
        logger.debug("cache_get miss (Redis unavailable): %s – %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl: int = None) -> None:
    """Set a cached value with optional TTL. No-op if Redis is unavailable."""
    try:
        client = await get_redis()
        serialised = json.dumps(value, default=str)
        await client.set(key, serialised, ex=ttl or settings.REDIS_CACHE_TTL)
    except (RedisConnectionError, Exception) as exc:
        logger.debug("cache_set skipped (Redis unavailable): %s – %s", key, exc)


async def cache_delete(key: str) -> None:
    """Delete a cached key. No-op if Redis is unavailable."""
    try:
        client = await get_redis()
        await client.delete(key)
    except (RedisConnectionError, Exception) as exc:
        logger.debug("cache_delete skipped (Redis unavailable): %s – %s", key, exc)


async def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern. No-op if Redis is unavailable."""
    try:
        client = await get_redis()
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
    except (RedisConnectionError, Exception) as exc:
        logger.debug(
            "cache_delete_pattern skipped (Redis unavailable): %s – %s", pattern, exc
        )
