"""
Cache Utilities

Helper functions for cache configuration and key generation.
"""

from typing import Any
from hashlib import md5

from faststack.core.cache.base import BaseCache
from faststack.core.cache.backends.locmem import LocMemCache


def get_cache(config: dict[str, Any]) -> BaseCache:
    """
    Create a cache backend from configuration.
    
    Args:
        config: Cache configuration dict with keys:
            - BACKEND: Backend class path (e.g., 'faststack.core.cache.backends.locmem.LocMemCache')
            - LOCATION: Backend-specific location (e.g., redis URL)
            - TIMEOUT: Default timeout
            - KEY_PREFIX: Key prefix
            - VERSION: Cache version
            - OPTIONS: Backend-specific options
    
    Returns:
        Configured cache instance
    
    Example:
        cache = get_cache({
            'BACKEND': 'faststack.core.cache.backends.redis.RedisCache',
            'LOCATION': 'redis://localhost:6379/1',
            'TIMEOUT': 300,
        })
    """
    if not config:
        return LocMemCache()
    
    backend_path = config.get('BACKEND', 'faststack.core.cache.backends.locmem.LocMemCache')
    
    # Import backend class
    module_path, class_name = backend_path.rsplit('.', 1)
    module = __import__(module_path, fromlist=[class_name])
    backend_class = getattr(module, class_name)
    
    # Get configuration
    kwargs = {
        'timeout': config.get('TIMEOUT', 300),
        'key_prefix': config.get('KEY_PREFIX', ''),
        'version': config.get('VERSION', 1),
    }
    
    # Add location if backend supports it
    if 'LOCATION' in config:
        kwargs['location'] = config['LOCATION']
    
    # Add backend-specific options
    if 'OPTIONS' in config:
        kwargs['options'] = config['OPTIONS']
    
    return backend_class(**kwargs)


def make_key(key: str, key_prefix: str = '', version: int = 1) -> str:
    """
    Construct a cache key.
    
    Args:
        key: Original key
        key_prefix: Key prefix
        version: Cache version
    
    Returns:
        Full cache key
    """
    if key_prefix:
        return f"{key_prefix}:{version}:{key}"
    return f"{version}:{key}"


def make_template_fragment_key(fragment_name: str, vary_on: list[Any] | None = None) -> str:
    """
    Make a cache key for a template fragment.
    
    Args:
        fragment_name: Name of the template fragment
        vary_on: List of values to vary the cache on
    
    Returns:
        Cache key for the fragment
    """
    if vary_on:
        vary_str = ':'.join(str(v) for v in vary_on)
        return f"template_fragment:{fragment_name}:{vary_str}"
    return f"template_fragment:{fragment_name}"


def hash_key(key: str) -> str:
    """
    Hash a long key to a fixed-length string.
    
    Useful for backends with key length limits.
    
    Args:
        key: Original key (can be long)
    
    Returns:
        Hashed key (32 characters)
    """
    return md5(key.encode()).hexdigest()


def generate_cache_key(
    prefix: str,
    *args,
    **kwargs,
) -> str:
    """
    Generate a cache key from function arguments.
    
    Args:
        prefix: Key prefix
        *args: Positional arguments to include
        **kwargs: Keyword arguments to include
    
    Returns:
        Generated cache key
    """
    parts = [prefix]
    
    # Add positional args
    for arg in args:
        parts.append(str(arg))
    
    # Add keyword args (sorted for consistency)
    for key in sorted(kwargs.keys()):
        parts.append(f"{key}={kwargs[key]}")
    
    return ':'.join(parts)


def get_cache_key_for_view(
    request,
    prefix: str = 'view',
    vary_on: list[str] | None = None,
) -> str:
    """
    Generate a cache key for a view.
    
    Args:
        request: FastAPI request object
        prefix: Key prefix
        vary_on: List of request attributes to vary on
    
    Returns:
        Cache key for the view
    """
    vary_on = vary_on or ['path', 'query']
    parts = [prefix]
    
    for vary in vary_on:
        if vary == 'path':
            parts.append(request.url.path)
        elif vary == 'query':
            query = str(request.query_params)
            if query:
                parts.append(query)
        elif vary == 'user':
            user_id = getattr(request, 'user', None)
            if user_id and hasattr(user_id, 'id'):
                parts.append(f"user:{user_id.id}")
        elif vary == 'method':
            parts.append(request.method)
        elif vary == 'headers':
            # Vary on specific headers
            pass
        else:
            # Try to get attribute from request
            value = getattr(request, vary, None)
            if value is not None:
                parts.append(str(value))
    
    return ':'.join(parts)
