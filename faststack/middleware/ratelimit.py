"""
FastStack Rate Limiting Middleware

Implements rate limiting using a sliding window algorithm.
Supports both in-memory and Redis backends.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional
import ipaddress

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from faststack.config import settings


def normalize_ip(ip: str) -> str:
    """
    Normalize IP address for consistent comparison.
    
    Handles IPv4-mapped IPv6 addresses.
    
    Args:
        ip: IP address string
    
    Returns:
        Normalized IP address
    """
    try:
        # Parse as IPv6 first (handles IPv4-mapped IPv6)
        addr = ipaddress.ip_address(ip)
        
        # Convert IPv4-mapped IPv6 to IPv4
        if addr.version == 6 and addr.ipv4_mapped:
            return str(addr.ipv4_mapped)
        
        return str(addr)
    except ValueError:
        return ip


def is_trusted_proxy(client_ip: str, trusted_proxies: list[str]) -> bool:
    """
    Check if an IP is a trusted proxy.
    
    Args:
        client_ip: IP address to check
        trusted_proxies: List of trusted proxy IPs/CIDRs
    
    Returns:
        True if IP is trusted
    """
    try:
        client = ipaddress.ip_address(client_ip)
        
        for proxy in trusted_proxies:
            if '/' in proxy:
                # CIDR notation
                if client in ipaddress.ip_network(proxy, strict=False):
                    return True
            else:
                # Single IP
                if client == ipaddress.ip_address(proxy):
                    return True
    except ValueError:
        pass
    
    return False


@dataclass
class RateLimitEntry:
    """Entry for tracking rate limit hits."""
    timestamps: list[float] = field(default_factory=list)
    blocked_until: float = 0


class RateLimiterBackend:
    """Base class for rate limiter backends."""
    
    async def is_allowed(self, key: str) -> tuple[bool, dict]:
        """Check if request is allowed."""
        raise NotImplementedError
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        raise NotImplementedError


class InMemoryBackend(RateLimiterBackend):
    """
    In-memory rate limiter backend using sliding window.
    
    Note: Not suitable for multi-worker deployments.
    Use Redis backend for production with multiple workers.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        block_duration: int = 300,
    ):
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
        """Check if request is allowed."""
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
            self._cleanup_old_timestamps(entry, 3600)
            
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


class RedisBackend(RateLimiterBackend):
    """
    Redis-backed rate limiter for distributed deployments.
    
    Uses sliding window algorithm with Lua scripts for atomic operations.
    """
    
    def __init__(
        self,
        redis_url: str,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        block_duration: int = 300,
        key_prefix: str = "ratelimit:",
    ):
        self.redis_url = redis_url
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.block_duration = block_duration
        self.key_prefix = key_prefix
        self._redis = None
        
        # Lua script for atomic check-and-increment
        self._script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        local block_duration = tonumber(ARGV[4])
        
        -- Check if blocked
        local blocked_until = redis.call('GET', key .. ':blocked')
        if blocked_until and tonumber(blocked_until) > now then
            return {0, tonumber(blocked_until) - now}
        end
        
        -- Remove old entries
        redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
        
        -- Count current entries
        local count = redis.call('ZCARD', key)
        
        if count >= limit then
            -- Block the key
            redis.call('SET', key .. ':blocked', now + block_duration, 'EX', block_duration)
            return {0, block_duration}
        end
        
        -- Add current request
        redis.call('ZADD', key, now, now .. ':' .. math.random())
        redis.call('EXPIRE', key, window)
        
        return {1, limit - count - 1}
        """
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.redis_url)
            except ImportError:
                raise RuntimeError(
                    "Redis backend requires 'redis' package. "
                    "Install it with: pip install redis"
                )
        return self._redis
    
    async def is_allowed(self, key: str) -> tuple[bool, dict]:
        """Check if request is allowed."""
        redis = await self._get_redis()
        
        redis_key = f"{self.key_prefix}{key}"
        now = time.time()
        
        # Check minute limit
        result = await redis.eval(
            self._script,
            1,
            f"{redis_key}:min",
            now,
            60,
            self.requests_per_minute,
            self.block_duration,
        )
        
        if result[0] == 0:
            return False, {
                "blocked": True,
                "limit": "minute",
                "retry_after": int(result[1]),
            }
        
        minute_remaining = result[1]
        
        # Check hour limit
        result = await redis.eval(
            self._script,
            1,
            f"{redis_key}:hour",
            now,
            3600,
            self.requests_per_hour,
            self.block_duration,
        )
        
        if result[0] == 0:
            return False, {
                "blocked": True,
                "limit": "hour",
                "retry_after": int(result[1]),
            }
        
        return True, {
            "blocked": False,
            "minute_remaining": minute_remaining,
            "hour_remaining": result[1],
        }
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        redis = await self._get_redis()
        redis_key = f"{self.key_prefix}{key}"
        
        await redis.delete(f"{redis_key}:min", f"{redis_key}:hour", f"{redis_key}:min:blocked", f"{redis_key}:hour:blocked")


class RateLimiter:
    """
    Rate limiter that supports multiple backends.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        block_duration: int = 300,
        redis_url: str | None = None,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.block_duration = block_duration
        
        # Choose backend
        if redis_url:
            self._backend = RedisBackend(
                redis_url=redis_url,
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_hour,
                block_duration=block_duration,
            )
        else:
            self._backend = InMemoryBackend(
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_hour,
                block_duration=block_duration,
            )
    
    async def is_allowed(self, key: str) -> tuple[bool, dict]:
        """Check if a request is allowed."""
        return await self._backend.is_allowed(key)
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        await self._backend.reset(key)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    
    Features:
    - Limits requests per IP address
    - Supports Redis for distributed deployments
    - Validates X-Forwarded-For from trusted proxies only
    - IP normalization for IPv4-mapped IPv6
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
        redis_url: str | None = None,
        trusted_proxies: list[str] | None = None,
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
            redis_url: Redis URL for distributed rate limiting
            trusted_proxies: List of trusted proxy IPs for X-Forwarded-For
        """
        super().__init__(app)
        self.limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            block_duration=block_duration,
            redis_url=redis_url,
        )
        self.key_func = key_func or self._default_key_func
        self.exempt_paths = exempt_paths or set()
        self.trusted_proxies = trusted_proxies or []
    
    def _default_key_func(self, request: Request) -> str:
        """Get default key (IP address) from request."""
        client_host = request.client.host if request.client else "unknown"
        
        # Check X-Forwarded-For only if from trusted proxy
        if self.trusted_proxies and is_trusted_proxy(client_host, self.trusted_proxies):
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                # Get the first IP in the chain (original client)
                first_ip = forwarded.split(",")[0].strip()
                return normalize_ip(first_ip)
            
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return normalize_ip(real_ip)
        
        # Fall back to direct client IP
        return normalize_ip(client_host)
    
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
        _rate_limiter = RateLimiter(
            redis_url=settings.RATE_LIMIT_REDIS_URL or None,
        )
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
    key = key or (request.client.host if request.client else "unknown")
    
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
