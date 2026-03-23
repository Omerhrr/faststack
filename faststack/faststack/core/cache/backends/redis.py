"""
Redis Cache Backend

Distributed cache using Redis. Suitable for production deployments.
"""

import time
import json
from typing import Any

from faststack.faststack.core.cache.base import BaseCache

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    aioredis = None


class RedisCache(BaseCache):
    """
    Redis cache backend.
    
    Suitable for production, multi-process, and distributed deployments.
    Supports async operations and connection pooling.
    
    Example:
        cache = RedisCache(
            location="redis://localhost:6379/1",
            timeout=300,
        )
        cache.set("key", "value")
    
    Configuration options:
        - location: Redis connection URL (redis://host:port/db)
        - options: Additional Redis options
            - max_connections: Max connection pool size
            - socket_timeout: Socket timeout in seconds
            - socket_connect_timeout: Connection timeout
    """
    
    def __init__(
        self,
        location: str = "redis://localhost:6379/0",
        timeout: int = 300,
        key_prefix: str = "",
        version: int = 1,
        options: dict | None = None,
        **kwargs,
    ):
        """
        Initialize Redis cache.
        
        Args:
            location: Redis connection URL
            timeout: Default timeout in seconds
            key_prefix: Prefix for all cache keys
            version: Cache version
            options: Additional Redis options
        """
        super().__init__(timeout, key_prefix, version, **kwargs)
        
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis package is required for RedisCache. "
                "Install with: pip install redis"
            )
        
        self.location = location
        self.options = options or {}
        
        # Parse Redis URL
        self._client: redis.Redis | None = None
        self._async_client: aioredis.Redis | None = None
    
    @property
    def client(self) -> redis.Redis:
        """Get or create the synchronous Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.location,
                max_connections=self.options.get('max_connections', 50),
                socket_timeout=self.options.get('socket_timeout', 5),
                socket_connect_timeout=self.options.get('socket_connect_timeout', 5),
                decode_responses=True,
            )
        return self._client
    
    @property
    def async_client(self) -> aioredis.Redis:
        """Get or create the asynchronous Redis client."""
        if self._async_client is None:
            self._async_client = aioredis.from_url(
                self.location,
                max_connections=self.options.get('max_connections', 50),
                socket_timeout=self.options.get('socket_timeout', 5),
                socket_connect_timeout=self.options.get('socket_connect_timeout', 5),
                decode_responses=True,
            )
        return self._async_client
    
    def _encode(self, value: Any) -> str:
        """Encode a value for storage."""
        return json.dumps(value, default=str)
    
    def _decode(self, value: str | None) -> Any:
        """Decode a value from storage."""
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    def add(self, key: str, value: Any, timeout: int | None = None) -> bool:
        """Add a value if key doesn't exist."""
        full_key = self.make_key(key)
        timeout = self.get_timeout(timeout)
        
        return self.client.set(
            full_key,
            self._encode(value),
            ex=timeout,
            nx=True,  # Only set if not exists
        ) or False
    
    def get(self, key: str, default: Any = None, version: int | None = None) -> Any:
        """Get a value from the cache."""
        full_key = self.make_key(key, version)
        value = self.client.get(full_key)
        
        if value is None:
            return default
        
        return self._decode(value)
    
    def set(self, key: str, value: Any, timeout: int | None = None) -> None:
        """Set a value in the cache."""
        full_key = self.make_key(key)
        timeout = self.get_timeout(timeout)
        
        self.client.set(
            full_key,
            self._encode(value),
            ex=timeout,
        )
    
    def touch(self, key: str, timeout: int | None = None, version: int | None = None) -> bool:
        """Update the timeout for a key."""
        full_key = self.make_key(key, version)
        timeout = self.get_timeout(timeout)
        
        return self.client.expire(full_key, timeout)
    
    def delete(self, key: str, version: int | None = None) -> bool:
        """Delete a key from the cache."""
        full_key = self.make_key(key, version)
        return bool(self.client.delete(full_key))
    
    def exists(self, key: str, version: int | None = None) -> bool:
        """Check if a key exists."""
        full_key = self.make_key(key, version)
        return bool(self.client.exists(full_key))
    
    def clear(self) -> None:
        """Clear all keys with this cache's prefix."""
        pattern = f"{self.key_prefix}:*"
        keys = self.client.keys(pattern)
        if keys:
            self.client.delete(*keys)
    
    def keys(self, pattern: str = "*") -> list[str]:
        """Get all keys matching a pattern."""
        full_pattern = self.make_key(pattern)
        keys = self.client.keys(full_pattern)
        
        # Strip prefix from keys
        prefix_len = len(f"{self.key_prefix}:{self.version}:")
        return [k[prefix_len:] for k in keys]
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        full_pattern = self.make_key(pattern)
        keys = self.client.keys(full_pattern)
        
        if keys:
            return self.client.delete(*keys)
        return 0
    
    def incr(self, key: str, delta: int = 1, version: int | None = None) -> int:
        """Increment a value atomically."""
        full_key = self.make_key(key, version)
        
        try:
            return self.client.incrby(full_key, delta)
        except redis.ResponseError:
            # Key doesn't exist or isn't an integer
            raise ValueError(f"Key '{key}' doesn't exist or isn't numeric")
    
    def get_many(self, keys: list[str], version: int | None = None) -> dict[str, Any]:
        """Get multiple values efficiently using mget."""
        full_keys = [self.make_key(k, version) for k in keys]
        values = self.client.mget(full_keys)
        
        result = {}
        for key, value in zip(keys, values):
            if value is not None:
                result[key] = self._decode(value)
        
        return result
    
    def set_many(self, data: dict[str, Any], timeout: int | None = None) -> None:
        """Set multiple values efficiently using mset."""
        if not data:
            return
        
        timeout = self.get_timeout(timeout)
        mapping = {
            self.make_key(k): self._encode(v)
            for k, v in data.items()
        }
        
        # Use pipeline for atomic set with expiry
        pipe = self.client.pipeline()
        pipe.mset(mapping)
        
        # Set expiry on each key
        if timeout:
            for key in mapping:
                pipe.expire(key, timeout)
        
        pipe.execute()
    
    def delete_many(self, keys: list[str], version: int | None = None) -> None:
        """Delete multiple keys efficiently."""
        full_keys = [self.make_key(k, version) for k in keys]
        if full_keys:
            self.client.delete(*full_keys)
    
    def close(self) -> None:
        """Close the connection."""
        if self._client:
            self._client.close()
            self._client = None
        
        if self._async_client:
            import asyncio
            asyncio.create_task(self._async_client.close())
            self._async_client = None
    
    # Async methods
    
    async def async_get(self, key: str, default: Any = None, version: int | None = None) -> Any:
        """Async get a value from the cache."""
        full_key = self.make_key(key, version)
        value = await self.async_client.get(full_key)
        
        if value is None:
            return default
        
        return self._decode(value)
    
    async def async_set(self, key: str, value: Any, timeout: int | None = None) -> None:
        """Async set a value in the cache."""
        full_key = self.make_key(key)
        timeout = self.get_timeout(timeout)
        
        await self.async_client.set(
            full_key,
            self._encode(value),
            ex=timeout,
        )
    
    async def async_delete(self, key: str, version: int | None = None) -> bool:
        """Async delete a key from the cache."""
        full_key = self.make_key(key, version)
        return bool(await self.async_client.delete(full_key))
