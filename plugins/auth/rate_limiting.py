"""
Enhanced Rate Limiting with Redis backend and exponential backoff.

Provides distributed rate limiting across multiple instances with:
- Sliding window counters
- Exponential backoff for repeated violations
- Per-IP and per-user rate limits
- Captcha challenge integration support
"""

from core.observability.logging import get_logger
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests: int  # Number of requests allowed
    window_seconds: int  # Time window in seconds
    ban_duration: int = 300  # Ban duration after limit exceeded (5 min default)
    exponential_backoff: bool = True  # Enable exponential backoff


class EnhancedRateLimiter:
    """
    Distributed rate limiter with Redis backend.

    Supports:
    - Sliding window algorithm
    - Per-IP and per-user limits
    - Exponential backoff for repeat offenders
    - Automatic cleanup of expired entries
    """

    def __init__(self, redis_client=None) -> None:
        """
        Initialize rate limiter.

        Args:
            redis_client: Optional Redis client (uses core Redis if None)
        """
        self.redis = redis_client
        self._use_redis = redis_client is not None

        if not self._use_redis:
            logger.warning(
                "Redis not available - using in-memory rate limiting "
                "(not suitable for multi-instance deployments)"
            )
            self._memory_store: dict = {}

    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate Redis key for rate limit."""
        return f"ratelimit:{endpoint}:{identifier}"

    def _get_ban_key(self, identifier: str, endpoint: str) -> str:
        """Generate Redis key for ban tracking."""
        return f"ratelimit:ban:{endpoint}:{identifier}"

    def _get_violations_key(self, identifier: str, endpoint: str) -> str:
        """Generate Redis key for violation count."""
        return f"ratelimit:violations:{endpoint}:{identifier}"

    async def is_rate_limited(
        self,
        identifier: str,
        endpoint: str,
        config: RateLimitConfig,
    ) -> tuple[bool, Optional[int]]:
        """
        Check if identifier is rate limited.

        Args:
            identifier: IP address or user ID
            endpoint: Endpoint identifier
            config: Rate limit configuration

        Returns:
            Tuple of (is_limited, retry_after_seconds)
        """
        now = time.time()
        key = self._get_key(identifier, endpoint)
        ban_key = self._get_ban_key(identifier, endpoint)
        violations_key = self._get_violations_key(identifier, endpoint)

        if self._use_redis:
            # Check if currently banned
            ban_until = await self._redis_get(ban_key)
            if ban_until and float(ban_until) > now:
                retry_after = int(float(ban_until) - now)
                return True, retry_after

            # Sliding window counter
            window_start = now - config.window_seconds

            # Get current count
            count = await self._redis_count_in_window(key, window_start, now)

            if count >= config.requests:
                # Limit exceeded - apply ban
                violations = await self._redis_incr(violations_key)

                # Exponential backoff
                if config.exponential_backoff:
                    ban_duration = config.ban_duration * (2 ** (violations - 1))
                    # Cap at 1 hour
                    ban_duration = min(ban_duration, 3600)
                else:
                    ban_duration = config.ban_duration

                ban_until_ts = now + ban_duration
                await self._redis_set(ban_key, ban_until_ts, ttl=ban_duration)
                await self._redis_set(violations_key, violations, ttl=3600)

                logger.warning(
                    f"Rate limit exceeded for {identifier} on {endpoint}. "
                    f"Ban duration: {ban_duration}s (violation #{violations})"
                )

                return True, ban_duration

            # Add current request to window
            await self._redis_add_to_window(key, now, config.window_seconds)

            return False, None

        else:
            # In-memory fallback (not distributed)
            return await self._memory_check(identifier, endpoint, config, now)

    async def _redis_get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        try:
            if hasattr(self.redis, "get"):
                result = await self.redis.get(key)
                return result.decode() if result else None
            return None
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    async def _redis_set(self, key: str, value, ttl: int) -> None:
        """Set value in Redis with TTL."""
        try:
            if hasattr(self.redis, "setex"):
                await self.redis.setex(key, ttl, str(value))
        except Exception as e:
            logger.error(f"Redis SET error: {e}")

    async def _redis_incr(self, key: str) -> int:
        """Increment counter in Redis."""
        try:
            if hasattr(self.redis, "incr"):
                return await self.redis.incr(key)
            return 1
        except Exception as e:
            logger.error(f"Redis INCR error: {e}")
            return 1

    async def _redis_count_in_window(
        self, key: str, window_start: float, now: float
    ) -> int:
        """Count requests in sliding window using sorted set."""
        try:
            if hasattr(self.redis, "zcount"):
                return await self.redis.zcount(key, window_start, now)
            return 0
        except Exception as e:
            logger.error(f"Redis ZCOUNT error: {e}")
            return 0

    async def _redis_add_to_window(
        self, key: str, timestamp: float, window_seconds: int
    ) -> None:
        """Add request timestamp to sorted set and cleanup old entries."""
        try:
            if hasattr(self.redis, "zadd") and hasattr(self.redis, "zremrangebyscore"):
                # Add current timestamp
                await self.redis.zadd(key, {str(timestamp): timestamp})

                # Remove old entries
                cutoff = timestamp - window_seconds
                await self.redis.zremrangebyscore(key, "-inf", cutoff)

                # Set expiration
                await self.redis.expire(key, window_seconds * 2)
        except Exception as e:
            logger.error(f"Redis window operations error: {e}")

    async def _memory_check(
        self, identifier: str, endpoint: str, config: RateLimitConfig, now: float
    ) -> tuple[bool, Optional[int]]:
        """In-memory rate limiting fallback."""
        key = f"{endpoint}:{identifier}"

        if key not in self._memory_store:
            self._memory_store[key] = {"requests": [], "ban_until": None}

        store = self._memory_store[key]

        # Check ban
        if store["ban_until"] and store["ban_until"] > now:
            retry_after = int(store["ban_until"] - now)
            return True, retry_after

        # Clean old requests
        window_start = now - config.window_seconds
        store["requests"] = [ts for ts in store["requests"] if ts > window_start]

        # Check limit
        if len(store["requests"]) >= config.requests:
            store["ban_until"] = now + config.ban_duration
            logger.warning(
                f"Rate limit exceeded for {identifier} on {endpoint} (in-memory)"
            )
            return True, config.ban_duration

        # Add request
        store["requests"].append(now)
        return False, None


# Global instance
_rate_limiter: Optional[EnhancedRateLimiter] = None


def get_rate_limiter() -> EnhancedRateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        # Try to use Redis from core
        try:
            from core.cache import get_cache_client

            redis_client = get_cache_client()
            _rate_limiter = EnhancedRateLimiter(redis_client=redis_client)
        except Exception as e:
            logger.warning(f"Could not initialize Redis rate limiter: {e}")
            _rate_limiter = EnhancedRateLimiter(redis_client=None)

    return _rate_limiter


def get_client_identifier(request: Request) -> str:
    """Extract the client identifier used to key rate-limit buckets.

    Trusted-proxy-aware: ``X-Forwarded-For`` is honoured only when the socket
    peer is a configured trusted proxy (``AUTH_TRUSTED_PROXIES``). Reading the
    header unconditionally let an attacker rotate it per request for a fresh
    bucket, defeating the login/MFA/reset throttles.
    """
    from plugins.auth.client_ip import trusted_client_ip

    return trusted_client_ip(request) or "unknown"


async def check_rate_limit(
    request: Request,
    endpoint: str,
    config: RateLimitConfig,
    user_id: Optional[str] = None,
) -> None:
    """
    Check rate limit and raise exception if exceeded.

    Args:
        request: FastAPI request
        endpoint: Endpoint identifier
        config: Rate limit configuration
        user_id: Optional user ID (takes precedence over IP)

    Raises:
        HTTPException: 429 Too Many Requests if limit exceeded
    """
    identifier = user_id or get_client_identifier(request)
    limiter = get_rate_limiter()

    is_limited, retry_after = await limiter.is_rate_limited(
        identifier, endpoint, config
    )

    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)} if retry_after else {},
        )


class RateLimit:
    """Rate-limiter dependency compatible with FastAPI ``Depends``.

    Backed by the Redis-distributed :class:`EnhancedRateLimiter` (via
    :func:`get_rate_limiter`) so per-IP limits hold across workers/instances and
    survive restarts, degrading to an in-memory window only when Redis is
    absent. It previously used the in-memory ``core.resilience`` limiter, which
    multiplied every limit by the worker count and reset on restart — so the
    login/MFA/reset throttles were effectively unbounded in production.
    """

    def __init__(
        self, times: int = 100, seconds: int = 60, endpoint: str | None = None
    ):
        self.times = times
        self.seconds = seconds
        self.endpoint = endpoint

    async def __call__(self, request: Request):
        identifier = get_client_identifier(request)
        endpoint = self.endpoint or request.url.path
        config = RateLimitConfig(requests=self.times, window_seconds=self.seconds)
        limiter = get_rate_limiter()
        is_limited, retry_after = await limiter.is_rate_limited(
            identifier, endpoint, config
        )
        if is_limited:
            wait = retry_after or 1
            logger.warning(
                "Rate limit exceeded for %s on %s. Retry after %ss",
                identifier,
                endpoint,
                wait,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Retry after {wait} seconds.",
                headers={"Retry-After": str(wait)},
            )
