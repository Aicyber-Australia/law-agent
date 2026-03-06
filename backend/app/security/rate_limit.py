"""Rate-limiting helpers with Redis backend and in-memory fallback."""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from app.config import REDIS_URL, logger

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None


class RateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._local: dict[str, list[float]] = defaultdict(list)
        self._redis = None

        if REDIS_URL and redis:
            try:
                self._redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
                self._redis.ping()
                logger.info("Redis-backed rate limiter enabled")
            except Exception as exc:
                logger.warning(
                    "Failed to initialize Redis rate limiter (%s). Falling back to local memory",
                    exc,
                )
                self._redis = None

    def allow(self, scope: str, identifier: str, limit: int, window_seconds: int) -> bool:
        if self._redis is not None:
            key = f"rl:{scope}:{identifier}:{int(time.time() // window_seconds)}"
            try:
                pipe = self._redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, window_seconds + 2)
                count, _ = pipe.execute()
                return int(count) <= limit
            except Exception as exc:
                logger.warning("Redis rate limit error (%s). Falling back to local check", exc)

        now = time.time()
        local_key = f"{scope}:{identifier}"
        with self._lock:
            timestamps = [ts for ts in self._local[local_key] if now - ts < window_seconds]
            if len(timestamps) >= limit:
                self._local[local_key] = timestamps
                return False
            timestamps.append(now)
            self._local[local_key] = timestamps
            return True


rate_limiter = RateLimiter()
