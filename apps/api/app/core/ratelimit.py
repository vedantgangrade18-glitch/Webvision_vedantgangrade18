"""Fixed-window rate limiting (Redis in staging/prod, in-memory locally)."""

from __future__ import annotations

import time

from app.core.config import get_settings
from app.core.errors import AppError

_memory: dict[str, tuple[int, float]] = {}
_redis = None


def _redis_client():
    global _redis
    if _redis is None:
        import redis.asyncio as redis

        _redis = redis.from_url(get_settings().redis_url)
    return _redis


async def hit(key: str, limit: int, window_s: int) -> bool:
    """Count one hit; return False when the limit is exceeded."""
    if get_settings().redis_url:
        r = _redis_client()
        bucket = f"rl:{key}:{int(time.time() // window_s)}"
        count = await r.incr(bucket)
        if count == 1:
            await r.expire(bucket, window_s)
        return count <= limit
    now = time.time()
    count, start = _memory.get(key, (0, now))
    if now - start >= window_s:
        count, start = 0, now
    count += 1
    _memory[key] = (count, start)
    return count <= limit


async def enforce(key: str, limit: int, window_s: int, code: str = "rate_limited") -> None:
    if not await hit(key, limit, window_s):
        raise AppError(429, code, details={"retry_after_s": window_s})


def reset_memory() -> None:
    _memory.clear()
