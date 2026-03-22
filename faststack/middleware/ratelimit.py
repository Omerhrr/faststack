"""
FastStack Rate Limiting Middleware

Implements rate limiting using a sliding window algorithm.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from faststack.config import settings


@dataclass
class RateLimitEntry:
    """Entry for tracking rate limit hits."""
    timestamps: list[float] = field(default_factory=list)
    blocked_until: float = 0


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.
    
    For production, replace with Redis-backed implementation.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        block_duration: int = 300,  # 5 minutes
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            block_duration: Duration to block in seconds after limit exceeded
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.block_duration = block_duration
        self._entries: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._lock = asyncio.Lock()
    
    def _cleanup_old_timestamps(self, entry: RateLimitEntry, window: float) -> None:
        """Remove timestamps outside the window."""
        cutoff = time.time() - window
        entry.timestamps = [ts for ts in entry.timestamps if ts > cutoff]
    
    async def is_allowed(self, key: str) -> tuple[bool, dict]:
        """
        Check if a request is allowed.
        
        Args:
            key: Identifier (usually IP address)
        
        Returns:
            Tuple of (is_allowed, info_dict)
        """
        async with self._lock:
            now = time.time()
            entry = self._entries[key]
            
            # Check if blocked
            if now < entry.blocked_until:
                return False, {
                    "blocked": True,
                    "retry_after": int(entry.blocked_until - now),
                }
            
            # Cleanup old timestamps
            self._cleanup_old_timestamps(entry, 3600)  # 1 hour window
            
            # Count requests in windows
            minute_ago = now - 60
            hour_ago = now - 3600
            
            minute_count = sum(1 for ts in entry.timestamps if ts > minute_ago)
            hour_count = len(entry.timestamps)
            
            # Check limits
            if minute_count >= self.requests_per_minute:
                entry.blocked_until = now + self.block_duration
                return False, {
                    "blocked": True,
                    "limit": "minute",
                    "retry_after": self.block_duration,
                    "requests_remaining": 0,
                }
            
            if hour_count >= self.requests_per_hour:
                entry.blocked_until = now + self.block_duration
                return False, {
                    "blocked": True,
                    "limit": "hour",
                    "retry_after": self.block_duration,
                    "requests_remaining": 0,
                }
            
            # Record this request
            entry.timestamps.append(now)
            
            return True, {
                "blocked": False,
                "minute_remaining": self.requests_per_minute - minute_count - 1,
                "hour_remaining": self.requests_per_hour - hour_count - 1,
            }
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        async with self._lock:
            if key in self._entries:
                del self._entries[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    
    Limits requests per IP address with configurable limits.
    """
    
    EXEMPT_PATHS = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/static",
    }
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        block_duration: int = 300,
        key_func: Callable[[Request], str] | None = None,
        exempt_paths: set[str] | None = None,
    ):
        """
        Initialize rate limit middleware.
        
        Args:
            app: ASGI application
            requests_per_minute: Max requests per minute per IP
            requests_per_hour: Max requests per hour per IP
            block_duration: Seconds to block after limit exceeded
            key_func: Function to extract key from request (default: IP)
            exempt_paths: Additional paths to exempt
        """
        super().__init__(app)
        self.limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            block_duration=block_duration,
        )
        self.key_func = key_func or self._default_key_func
        self.exempt_paths = exempt_paths or set()
    
    def _default_key_func(self, request: Request) -> str:
        """Get default key (IP address) from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        if path in self.EXEMPT_PATHS or path in self.exempt_paths:
            return True
        
        for exempt in self.EXEMPT_PATHS:
            if path.startswith(exempt):
                return True
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        path = request.url.path
        
        if self._is_exempt(path):
            return await call_next(request)
        
        key = self.key_func(request)
        allowed, info = await self.limiter.is_allowed(key)
        
        if not allowed:
            response = JSONResponse(
                {
                    "detail": "Rate limit exceeded",
                    "retry_after": info.get("retry_after", 60),
                },
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response.headers["Retry-After"] = str(info.get("retry_after", 60))
            response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = "0"
            return response
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(info.get("minute_remaining", 0))
        
        return response


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def check_rate_limit(request: Request, key: str | None = None) -> dict:
    """
    Check rate limit for a request.
    
    Args:
        request: FastAPI request
        key: Optional key (default: IP address)
    
    Returns:
        Rate limit info dict
    
    Raises:
        HTTPException: If rate limit exceeded
    """
    limiter = get_rate_limiter()
    key = key or request.client.host if request.client else "unknown"
    
    allowed, info = await limiter.is_allowed(key)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Rate limit exceeded",
                "retry_after": info.get("retry_after", 60),
            },
        )
    
    return info
