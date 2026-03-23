"""
FastStack Cache Base Class

Defines the interface that all cache backends must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseCache(ABC):
    """
    Base class for all cache backends.
    
    All cache backends must implement these methods to provide
    a consistent interface.
    """
    
    def __init__(
        self,
        timeout: int = 300,
        key_prefix: str = "",
        version: int = 1,
        **kwargs,
    ):
        """
        Initialize the cache.
        
        Args:
            timeout: Default timeout in seconds
            key_prefix: Prefix for all cache keys
            version: Cache version (for cache invalidation)
            **kwargs: Backend-specific options
        """
        self.default_timeout = timeout
        self.key_prefix = key_prefix
        self.version = version
    
    def make_key(self, key: str, version: int | None = None) -> str:
        """
        Construct the full cache key.
        
        Args:
            key: The original key
            version: Optional version override
        
        Returns:
            Full cache key with prefix and version
        """
        if version is None:
            version = self.version
        return f"{self.key_prefix}:{version}:{key}"
    
    @abstractmethod
    def add(self, key: str, value: Any, timeout: int | None = None) -> bool:
        """
        Add a value to the cache if it doesn't already exist.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Timeout in seconds (uses default if None)
        
        Returns:
            True if the value was added, False if key already exists
        """
        pass
    
    @abstractmethod
    def get(self, key: str, default: Any = None, version: int | None = None) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            version: Optional version override
        
        Returns:
            The cached value or default
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, timeout: int | None = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Timeout in seconds (uses default if None)
        """
        pass
    
    @abstractmethod
    def touch(self, key: str, timeout: int | None = None, version: int | None = None) -> bool:
        """
        Update the timeout for a key.
        
        Args:
            key: Cache key
            timeout: New timeout in seconds
            version: Optional version override
        
        Returns:
            True if successful, False if key doesn't exist
        """
        pass
    
    @abstractmethod
    def delete(self, key: str, version: int | None = None) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            key: Cache key
            version: Optional version override
        
        Returns:
            True if deleted, False if key didn't exist
        """
        pass
    
    @abstractmethod
    def exists(self, key: str, version: int | None = None) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: Cache key
            version: Optional version override
        
        Returns:
            True if key exists
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """
        Clear all keys from the cache.
        
        Use with caution!
        """
        pass
    
    def get_many(self, keys: list[str], version: int | None = None) -> dict[str, Any]:
        """
        Get multiple values from the cache.
        
        Args:
            keys: List of cache keys
            version: Optional version override
        
        Returns:
            Dict of key -> value for found keys
        """
        result = {}
        for key in keys:
            value = self.get(key, version=version)
            if value is not None:
                result[key] = value
        return result
    
    def set_many(self, data: dict[str, Any], timeout: int | None = None) -> None:
        """
        Set multiple values in the cache.
        
        Args:
            data: Dict of key -> value to set
            timeout: Timeout in seconds
        """
        for key, value in data.items():
            self.set(key, value, timeout)
    
    def delete_many(self, keys: list[str], version: int | None = None) -> None:
        """
        Delete multiple keys from the cache.
        
        Args:
            keys: List of cache keys
            version: Optional version override
        """
        for key in keys:
            self.delete(key, version)
    
    def incr(self, key: str, delta: int = 1, version: int | None = None) -> int:
        """
        Increment a value.
        
        Args:
            key: Cache key
            delta: Amount to increment
            version: Optional version override
        
        Returns:
            New value after increment
        
        Raises:
            ValueError: If key doesn't exist or value isn't numeric
        """
        value = self.get(key, version=version)
        if value is None:
            raise ValueError(f"Key '{key}' not found")
        
        try:
            new_value = int(value) + delta
        except (TypeError, ValueError):
            raise ValueError(f"Value for key '{key}' is not numeric")
        
        self.set(key, new_value, version=version)
        return new_value
    
    def decr(self, key: str, delta: int = 1, version: int | None = None) -> int:
        """
        Decrement a value.
        
        Args:
            key: Cache key
            delta: Amount to decrement
            version: Optional version override
        
        Returns:
            New value after decrement
        """
        return self.incr(key, -delta, version)
    
    def get_or_set(
        self,
        key: str,
        default: Any | callable,
        timeout: int | None = None,
        version: int | None = None,
    ) -> Any:
        """
        Get a value or set it if it doesn't exist.
        
        Args:
            key: Cache key
            default: Value to set if key doesn't exist (can be callable)
            timeout: Timeout in seconds
            version: Optional version override
        
        Returns:
            The cached or newly set value
        """
        value = self.get(key, version=version)
        if value is not None:
            return value
        
        if callable(default):
            value = default()
        else:
            value = default
        
        self.set(key, value, timeout, version)
        return value
    
    def has_key(self, key: str, version: int | None = None) -> bool:
        """Alias for exists()."""
        return self.exists(key, version)
    
    def keys(self, pattern: str = "*") -> list[str]:
        """
        Get all keys matching a pattern.
        
        Not all backends support this efficiently.
        
        Args:
            pattern: Key pattern (supports * wildcard)
        
        Returns:
            List of matching keys
        """
        raise NotImplementedError("This cache backend does not support keys()")
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Not all backends support this efficiently.
        
        Args:
            pattern: Key pattern (supports * wildcard)
        
        Returns:
            Number of keys deleted
        """
        raise NotImplementedError("This cache backend does not support delete_pattern()")
    
    def get_timeout(self, timeout: int | None) -> int:
        """
        Get the effective timeout.
        
        Args:
            timeout: Timeout value or None
        
        Returns:
            Effective timeout in seconds
        """
        if timeout is None:
            return self.default_timeout
        return timeout
    
    def close(self) -> None:
        """
        Close the cache connection.
        
        Override in backends that need cleanup.
        """
        pass
    
    def __contains__(self, key: str) -> bool:
        return self.exists(key)
    
    def __getitem__(self, key: str) -> Any:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value
    
    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)
    
    def __delitem__(self, key: str) -> None:
        self.delete(key)
