"""
FastStack Caching Framework

A Django-like caching framework with multiple backend support.

Features:
- In-memory cache (LocMemCache)
- Redis cache
- Database cache
- File-based cache
- Cache decorators for views
- Template caching

Example:
    from faststack.core.cache import cache
    
    # Set a value
    cache.set("user:1", user_data, timeout=300)
    
    # Get a value
    user = cache.get("user:1")
    
    # Delete
    cache.delete("user:1")
    
    # Decorator
    @cache_page(60)
    async def my_view(request):
        return {"data": "..."}
"""

from faststack.faststack.core.cache.base import BaseCache
from faststack.faststack.core.cache.backends.locmem import LocMemCache
from faststack.faststack.core.cache.decorators import cache_page, cache_control
from faststack.faststack.core.cache.utils import get_cache, make_key

# Default cache instance
_cache: BaseCache | None = None


def get_default_cache() -> BaseCache:
    """Get the default cache instance."""
    global _cache
    if _cache is None:
        from faststack.config import settings
        _cache = get_cache(settings.CACHES.get('default', {}))
    return _cache


# Create a proxy object that delegates to the default cache
class CacheProxy:
    """Proxy object that delegates to the default cache."""
    
    def __getattr__(self, name):
        return getattr(get_default_cache(), name)


cache = CacheProxy()


__all__ = [
    "BaseCache",
    "LocMemCache",
    "cache_page",
    "cache_control",
    "get_cache",
    "make_key",
    "cache",
]
