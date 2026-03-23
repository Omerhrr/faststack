"""
Cache Decorators

Decorators for caching views and functions.
"""

from functools import wraps
from typing import Callable, Any

from fastapi import Request


def cache_page(
    timeout: int,
    *,
    cache: Any = None,
    key_prefix: str | None = None,
    cache_control: str | None = None,
) -> Callable:
    """
    Decorator to cache a view's response.
    
    Args:
        timeout: Cache timeout in seconds
        cache: Cache backend to use (default: global cache)
        key_prefix: Custom key prefix
        cache_control: Cache-Control header value
    
    Returns:
        Decorator function
    
    Example:
        @cache_page(60 * 15)  # Cache for 15 minutes
        async def expensive_view(request: Request):
            # Expensive computation
            return {"data": "..."}
        
        @cache_page(300, key_prefix="user_detail")
        async def user_detail(request: Request, user_id: int):
            return {"user_id": user_id}
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        async def wrapped_view(request: Request, *args, **kwargs):
            # Get cache backend
            cache_backend = cache
            if cache_backend is None:
                from faststack.core.cache import cache as default_cache
                cache_backend = default_cache
            
            # Generate cache key
            from faststack.core.cache.utils import get_cache_key_for_view
            prefix = key_prefix or f"view:{view_func.__name__}"
            cache_key = get_cache_key_for_view(request, prefix=prefix)
            
            # Try to get from cache
            cached_response = cache_backend.get(cache_key)
            if cached_response is not None:
                return cached_response
            
            # Call view
            response = await view_func(request, *args, **kwargs)
            
            # Cache the response
            if response is not None:
                cache_backend.set(cache_key, response, timeout)
            
            return response
        
        return wrapped_view
    return decorator


def cache_control(**kwargs) -> Callable:
    """
    Decorator to add Cache-Control headers to a response.
    
    Args:
        **kwargs: Cache-Control directives
            - max_age: Maximum age in seconds
            - public: Allow shared caching
            - private: Response is for single user
            - no_cache: Must revalidate
            - no_store: Don't cache
            - must_revalidate: Must revalidate stale responses
    
    Returns:
        Decorator function
    
    Example:
        @cache_control(max_age=3600, public=True)
        async def public_view(request):
            return {"data": "..."}
    """
    directives = []
    
    if 'max_age' in kwargs:
        directives.append(f"max-age={kwargs['max_age']}")
    if 's_maxage' in kwargs:
        directives.append(f"s-maxage={kwargs['s_maxage']}")
    if kwargs.get('public'):
        directives.append("public")
    if kwargs.get('private'):
        directives.append("private")
    if kwargs.get('no_cache'):
        directives.append("no-cache")
    if kwargs.get('no_store'):
        directives.append("no-store")
    if kwargs.get('must_revalidate'):
        directives.append("must-revalidate")
    if kwargs.get('proxy_revalidate'):
        directives.append("proxy-revalidate")
    if kwargs.get('no_transform'):
        directives.append("no-transform")
    
    cache_control_value = ', '.join(directives)
    
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        async def wrapped_view(request: Request, *args, **kwargs):
            response = await view_func(request, *args, **kwargs)
            
            # Add header to response
            if hasattr(response, 'headers'):
                response.headers['Cache-Control'] = cache_control_value
            
            return response
        
        return wrapped_view
    return decorator


def vary_on_headers(*headers: str) -> Callable:
    """
    Decorator to add Vary headers to a response.
    
    This tells caches to vary the cached response based on
    the specified request headers.
    
    Args:
        *headers: Header names to vary on
    
    Returns:
        Decorator function
    
    Example:
        @vary_on_headers('User-Agent', 'Accept-Language')
        async def personalized_view(request):
            return {"data": "..."}
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        async def wrapped_view(request: Request, *args, **kwargs):
            response = await view_func(request, *args, **kwargs)
            
            # Add Vary header
            if hasattr(response, 'headers'):
                existing_vary = response.headers.get('Vary', '')
                all_headers = list(headers)
                if existing_vary:
                    all_headers.extend(h.strip() for h in existing_vary.split(','))
                response.headers['Vary'] = ', '.join(all_headers)
            
            return response
        
        return wrapped_view
    return decorator


def cache_on_arguments(
    timeout: int = 300,
    *,
    key_prefix: str | None = None,
    cache: Any = None,
) -> Callable:
    """
    Decorator to cache function results based on arguments.
    
    Useful for caching expensive computations.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Custom key prefix
        cache: Cache backend to use
    
    Returns:
        Decorator function
    
    Example:
        @cache_on_arguments(timeout=60)
        def expensive_computation(n: int):
            # Expensive operation
            return sum(range(n))
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache backend
            cache_backend = cache
            if cache_backend is None:
                from faststack.core.cache import cache as default_cache
                cache_backend = default_cache
            
            # Generate key
            from faststack.core.cache.utils import generate_cache_key
            prefix = key_prefix or f"func:{func.__module__}.{func.__name__}"
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            
            # Try cache
            cached = cache_backend.get(cache_key)
            if cached is not None:
                return cached
            
            # Call function
            result = func(*args, **kwargs)
            
            # Cache result
            cache_backend.set(cache_key, result, timeout)
            
            return result
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get cache backend
            cache_backend = cache
            if cache_backend is None:
                from faststack.core.cache import cache as default_cache
                cache_backend = default_cache
            
            # Generate key
            from faststack.core.cache.utils import generate_cache_key
            prefix = key_prefix or f"func:{func.__module__}.{func.__name__}"
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            
            # Try cache
            cached = cache_backend.get(cache_key)
            if cached is not None:
                return cached
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache_backend.set(cache_key, result, timeout)
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


def never_cache(view_func: Callable) -> Callable:
    """
    Decorator to prevent caching of a view.
    
    Adds headers to prevent any caching.
    
    Example:
        @never_cache
        async def sensitive_view(request):
            return {"secret": "data"}
    """
    @wraps(view_func)
    async def wrapped_view(request: Request, *args, **kwargs):
        response = await view_func(request, *args, **kwargs)
        
        if hasattr(response, 'headers'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        return response
    
    return wrapped_view
