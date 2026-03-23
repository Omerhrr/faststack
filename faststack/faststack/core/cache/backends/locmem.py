"""
In-Memory Cache Backend

Simple in-memory cache for single-process applications.
Uses a dictionary with TTL tracking.
"""

import time
from threading import RLock
from typing import Any
import fnmatch

from faststack.core.cache.base import BaseCache


class LocMemCache(BaseCache):
    """
    In-memory cache backend.
    
    Suitable for development and single-process deployments.
    Uses a dictionary with expiration tracking.
    
    Example:
        cache = LocMemCache(timeout=300, max_entries=1000)
        cache.set("key", "value")
        cache.get("key")  # "value"
    
    Note: Each process has its own cache, so this is not suitable
    for multi-process or distributed deployments.
    """
    
    def __init__(
        self,
        timeout: int = 300,
        key_prefix: str = "",
        version: int = 1,
        max_entries: int = 300,
        cull_frequency: int = 3,
        **kwargs,
    ):
        """
        Initialize the in-memory cache.
        
        Args:
            timeout: Default timeout in seconds
            key_prefix: Prefix for all cache keys
            version: Cache version
            max_entries: Maximum number of entries
            cull_frequency: Fraction of entries to cull when full (1/cull_frequency)
        """
        super().__init__(timeout, key_prefix, version, **kwargs)
        self.max_entries = max_entries
        self.cull_frequency = cull_frequency
        
        # Cache storage: key -> (value, expiry_time)
        self._cache: dict[str, tuple[Any, float]] = {}
        
        # Thread safety
        self._lock = RLock()
    
    def _cull(self) -> None:
        """Remove expired entries and cull if over capacity."""
        now = time.time()
        
        # Remove expired entries
        expired_keys = [
            key for key, (_, expiry) in self._cache.items()
            if expiry < now
        ]
        for key in expired_keys:
            del self._cache[key]
        
        # Cull if still over capacity
        if len(self._cache) >= self.max_entries:
            # Remove 1/cull_frequency of entries
            cull_count = len(self._cache) // self.cull_frequency
            keys_to_remove = list(self._cache.keys())[:cull_count]
            for key in keys_to_remove:
                del self._cache[key]
    
    def add(self, key: str, value: Any, timeout: int | None = None) -> bool:
        """Add a value if key doesn't exist."""
        full_key = self.make_key(key)
        
        with self._lock:
            # Check if key exists and is not expired
            if full_key in self._cache:
                _, expiry = self._cache[full_key]
                if expiry > time.time():
                    return False
            
            # Set the value
            self.set(key, value, timeout)
            return True
    
    def get(self, key: str, default: Any = None, version: int | None = None) -> Any:
        """Get a value from the cache."""
        full_key = self.make_key(key, version)
        
        with self._lock:
            if full_key not in self._cache:
                return default
            
            value, expiry = self._cache[full_key]
            
            # Check if expired
            if expiry < time.time():
                del self._cache[full_key]
                return default
            
            return value
    
    def set(self, key: str, value: Any, timeout: int | None = None) -> None:
        """Set a value in the cache."""
        full_key = self.make_key(key)
        timeout = self.get_timeout(timeout)
        expiry = time.time() + timeout
        
        with self._lock:
            # Cull if needed
            if len(self._cache) >= self.max_entries:
                self._cull()
            
            self._cache[full_key] = (value, expiry)
    
    def touch(self, key: str, timeout: int | None = None, version: int | None = None) -> bool:
        """Update the timeout for a key."""
        full_key = self.make_key(key, version)
        
        with self._lock:
            if full_key not in self._cache:
                return False
            
            value, _ = self._cache[full_key]
            timeout = self.get_timeout(timeout)
            expiry = time.time() + timeout
            self._cache[full_key] = (value, expiry)
            return True
    
    def delete(self, key: str, version: int | None = None) -> bool:
        """Delete a key from the cache."""
        full_key = self.make_key(key, version)
        
        with self._lock:
            if full_key in self._cache:
                del self._cache[full_key]
                return True
            return False
    
    def exists(self, key: str, version: int | None = None) -> bool:
        """Check if a key exists."""
        full_key = self.make_key(key, version)
        
        with self._lock:
            if full_key not in self._cache:
                return False
            
            _, expiry = self._cache[full_key]
            if expiry < time.time():
                del self._cache[full_key]
                return False
            
            return True
    
    def clear(self) -> None:
        """Clear all keys from the cache."""
        with self._lock:
            self._cache.clear()
    
    def keys(self, pattern: str = "*") -> list[str]:
        """
        Get all keys matching a pattern.
        
        Args:
            pattern: Key pattern (supports * wildcard)
        
        Returns:
            List of matching keys (without prefix)
        """
        now = time.time()
        result = []
        
        with self._lock:
            for full_key, (_, expiry) in self._cache.items():
                if expiry < now:
                    continue
                
                # Remove prefix and version from key
                parts = full_key.split(":", 2)
                if len(parts) >= 3:
                    key = parts[2]
                else:
                    key = full_key
                
                if fnmatch.fnmatch(key, pattern):
                    result.append(key)
        
        return result
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        keys = self.keys(pattern)
        count = 0
        
        with self._lock:
            for key in keys:
                full_key = self.make_key(key)
                if full_key in self._cache:
                    del self._cache[full_key]
                    count += 1
        
        return count
    
    def incr(self, key: str, delta: int = 1, version: int | None = None) -> int:
        """Increment a value atomically."""
        full_key = self.make_key(key, version)
        
        with self._lock:
            if full_key not in self._cache:
                raise ValueError(f"Key '{key}' not found")
            
            value, expiry = self._cache[full_key]
            try:
                new_value = int(value) + delta
            except (TypeError, ValueError):
                raise ValueError(f"Value for key '{key}' is not numeric")
            
            self._cache[full_key] = (new_value, expiry)
            return new_value
    
    def get_many(self, keys: list[str], version: int | None = None) -> dict[str, Any]:
        """Get multiple values efficiently."""
        result = {}
        now = time.time()
        
        with self._lock:
            for key in keys:
                full_key = self.make_key(key, version)
                if full_key in self._cache:
                    value, expiry = self._cache[full_key]
                    if expiry > now:
                        result[key] = value
        
        return result
    
    def set_many(self, data: dict[str, Any], timeout: int | None = None) -> None:
        """Set multiple values efficiently."""
        timeout = self.get_timeout(timeout)
        expiry = time.time() + timeout
        
        with self._lock:
            # Cull if needed
            if len(self._cache) + len(data) >= self.max_entries:
                self._cull()
            
            for key, value in data.items():
                full_key = self.make_key(key)
                self._cache[full_key] = (value, expiry)
    
    def delete_many(self, keys: list[str], version: int | None = None) -> None:
        """Delete multiple keys efficiently."""
        with self._lock:
            for key in keys:
                full_key = self.make_key(key, version)
                if full_key in self._cache:
                    del self._cache[full_key]
    
    def __len__(self) -> int:
        """Return the number of entries in the cache."""
        with self._lock:
            # Count only non-expired entries
            now = time.time()
            return sum(1 for _, (_, expiry) in self._cache.items() if expiry > now)
