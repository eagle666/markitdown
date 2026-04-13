"""Rate limiting middleware using sliding window."""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.config import settings


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a tenant."""
    requests: int
    window_seconds: int


@dataclass
class RateLimitState:
    """State for a single rate limit window."""
    count: int = 0
    window_start: float = 0.0


class SlidingWindowRateLimiter:
    """
    A sliding window rate limiter implementation.

    Tracks request counts per key (e.g., API key) using a sliding window
    algorithm for accurate rate limiting.
    """

    def __init__(
        self,
        requests: int = 100,
        window_seconds: int = 60,
    ):
        self.requests = requests
        self.window_seconds = window_seconds
        self._state: dict[str, RateLimitState] = defaultdict(
            lambda: RateLimitState(window_start=time.time())
        )
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> tuple[bool, dict]:
        """
        Check if a request is allowed for the given key.

        Args:
            key: The identifier (usually API key).

        Returns:
            Tuple of (is_allowed, info_dict)
        """
        now = time.time()

        with self._lock:
            state = self._state[key]

            # Reset window if expired
            if now - state.window_start >= self.window_seconds:
                state.count = 0
                state.window_start = now

            # Check limit
            if state.count >= self.requests:
                remaining = 0
                retry_after = int(self.window_seconds - (now - state.window_start))
                return False, {
                    "remaining": remaining,
                    "limit": self.requests,
                    "reset": int(state.window_start + self.window_seconds),
                    "retry_after": retry_after,
                }

            # Increment counter
            state.count += 1
            remaining = self.requests - state.count

            return True, {
                "remaining": remaining,
                "limit": self.requests,
                "reset": int(state.window_start + self.window_seconds),
            }


# Global rate limiter (per worker process)
_rate_limiter: Optional[SlidingWindowRateLimiter] = None


def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = SlidingWindowRateLimiter(
            requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limiting based on API key.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("X-API-Key", "anonymous")

        limiter = get_rate_limiter()
        allowed, info = limiter.is_allowed(api_key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Try again in {info['retry_after']} seconds.",
                        "retry_after": info["retry_after"],
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["retry_after"]),
                },
            )

        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response


# Dependency for routes that need explicit rate limit checking
async def check_rate_limit(request: Request) -> dict:
    """Dependency to check rate limit for a request."""
    api_key = request.headers.get("X-API-Key", "anonymous")
    limiter = get_rate_limiter()
    allowed, info = limiter.is_allowed(api_key)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Try again in {info['retry_after']} seconds.",
                    "retry_after": info["retry_after"],
                }
            },
        )

    return info


def rate_limit_middleware() -> RateLimitMiddleware:
    """Factory function for rate limit middleware."""
    return RateLimitMiddleware