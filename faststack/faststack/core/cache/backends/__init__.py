"""
Cache Backend Package
"""

from faststack.faststack.core.cache.backends.locmem import LocMemCache

__all__ = [
    "LocMemCache",
]

# Conditionally import Redis if available
try:
    from faststack.faststack.core.cache.backends.redis import RedisCache
    __all__.append("RedisCache")
except ImportError:
    RedisCache = None  # type: ignore

# Conditionally import Database cache
try:
    from faststack.faststack.core.cache.backends.database import DatabaseCache
    __all__.append("DatabaseCache")
except ImportError:
    DatabaseCache = None  # type: ignore
