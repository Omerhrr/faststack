"""
FastStack Decorators - HTTP and view decorators.

Example:
    from faststack.core.decorators import (
        cache_control,
        require_http_methods,
        require_GET,
        require_POST,
        vary_on_headers,
        vary_on_cookie,
        condition,
        etag,
        last_modified
    )

    @require_POST
    @cache_control(max_age=3600, public=True)
    async def create_post(request):
        ...

    @etag(lambda r: r.content_hash)
    async def get_content(request):
        ...
"""

from typing import Any, Callable, List, Optional, Union
from functools import wraps
import hashlib
import time
from starlette.responses import Response
from starlette.exceptions import HTTPException


def cache_control(**kwargs):
    """
    Decorator to set Cache-Control header.

    Args:
        **kwargs: Cache-Control directives (max_age, public, private, no_cache, etc.)

    Example:
        @cache_control(max_age=3600, public=True)
        async def view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        async def wrapped_view(request, *args, **inner_kwargs):
            response = await view_func(request, *args, **inner_kwargs)

            if hasattr(response, 'headers'):
                directives = []
                for key, value in kwargs.items():
                    key = key.replace('_', '-')
                    if value is True:
                        directives.append(key)
                    elif value is not False and value is not None:
                        directives.append(f"{key}={value}")
                response.headers['Cache-Control'] = ', '.join(directives)

            return response
        return wrapped_view
    return decorator


def vary_on_headers(*headers: str):
    """
    Decorator to set Vary header.

    Args:
        *headers: Headers to vary on

    Example:
        @vary_on_headers('User-Agent', 'Accept-Language')
        async def view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        async def wrapped_view(request, *args, **inner_kwargs):
            response = await view_func(request, *args, **inner_kwargs)

            if hasattr(response, 'headers'):
                existing = response.headers.get('Vary', '')
                all_headers = list(headers)
                if existing:
                    all_headers.extend(h.strip() for h in existing.split(','))
                response.headers['Vary'] = ', '.join(all_headers)

            return response
        return wrapped_view
    return decorator


def vary_on_cookie(view_func: Callable = None):
    """
    Decorator to add Cookie to Vary header.

    Example:
        @vary_on_cookie
        async def view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapped(request, *args, **kwargs):
            response = await func(request, *args, **kwargs)
            if hasattr(response, 'headers'):
                existing = response.headers.get('Vary', '')
                headers = ['Cookie']
                if existing:
                    headers.extend(h.strip() for h in existing.split(','))
                response.headers['Vary'] = ', '.join(headers)
            return response
        return wrapped

    if view_func:
        return decorator(view_func)
    return decorator


def require_http_methods(methods: List[str]):
    """
    Decorator to require specific HTTP methods.

    Args:
        methods: List of allowed methods

    Example:
        @require_http_methods(['GET', 'POST'])
        async def view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        async def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                raise HTTPException(
                    status_code=405,
                    detail=f"Method {request.method} not allowed. Allowed: {', '.join(methods)}"
                )
            return await view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def require_GET(view_func: Callable):
    """Decorator to require GET method."""
    @wraps(view_func)
    async def wrapped(request, *args, **kwargs):
        if request.method != 'GET':
            raise HTTPException(status_code=405, detail="Method not allowed. Use GET.")
        return await view_func(request, *args, **kwargs)
    return wrapped


def require_POST(view_func: Callable):
    """Decorator to require POST method."""
    @wraps(view_func)
    async def wrapped(request, *args, **kwargs):
        if request.method != 'POST':
            raise HTTPException(status_code=405, detail="Method not allowed. Use POST.")
        return await view_func(request, *args, **kwargs)
    return wrapped


def require_safe(view_func: Callable):
    """Decorator to require safe methods (GET, HEAD, OPTIONS)."""
    @wraps(view_func)
    async def wrapped(request, *args, **kwargs):
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            raise HTTPException(status_code=405, detail="Method not allowed. Safe methods only.")
        return await view_func(request, *args, **kwargs)
    return wrapped


def condition(
    etag_func: Callable = None,
    last_modified_func: Callable = None
):
    """
    Decorator for conditional request handling.

    Args:
        etag_func: Function to compute ETag
        last_modified_func: Function to compute Last-Modified

    Example:
        @condition(
            etag_func=lambda r: compute_etag(r),
            last_modified_func=lambda r: get_last_modified(r)
        )
        async def view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        async def wrapped(request, *args, **kwargs):
            # Compute ETag
            etag = None
            if etag_func:
                etag = await etag_func(request) if asyncio.iscoroutinefunction(etag_func) else etag_func(request)

            # Compute Last-Modified
            last_modified = None
            if last_modified_func:
                lm = last_modified_func(request)
                if asyncio.iscoroutine(lm):
                    lm = await lm
                last_modified = lm

            # Check If-None-Match
            if_none_match = request.headers.get('if-none-match')
            if etag and if_none_match:
                if etag in if_none_match or '*' in if_none_match:
                    return Response(status_code=304)

            # Check If-Modified-Since
            if_modified_since = request.headers.get('if-modified-since')
            if last_modified and if_modified_since:
                # Parse date and compare
                try:
                    from email.utils import parsedate_to_datetime
                    ims_date = parsedate_to_datetime(if_modified_since)
                    if last_modified <= ims_date:
                        return Response(status_code=304)
                except:
                    pass

            # Execute view
            response = await view_func(request, *args, **kwargs)

            # Add headers
            if etag and hasattr(response, 'headers'):
                response.headers['ETag'] = f'"{etag}"'
            if last_modified and hasattr(response, 'headers'):
                from email.utils import formatdate
                response.headers['Last-Modified'] = formatdate(
                    time.mktime(last_modified.timetuple()),
                    usegmt=True
                )

            return response
        return wrapped
    return decorator


def etag(etag_func: Callable):
    """
    Decorator to add ETag header.

    Example:
        @etag(lambda r: hashlib.md5(r.content).hexdigest())
        async def view(request):
            ...
    """
    return condition(etag_func=etag_func)


def last_modified(last_modified_func: Callable):
    """
    Decorator to add Last-Modified header.

    Example:
        @last_modified(lambda r: get_object().updated_at)
        async def view(request):
            ...
    """
    return condition(last_modified_func=last_modified_func)


def gzip_compressed(view_func: Callable = None, minimum_size: int = 1000):
    """
    Decorator to enable gzip compression.

    Args:
        minimum_size: Minimum response size to compress

    Example:
        @gzip_compressed
        async def view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapped(request, *args, **kwargs):
            response = await func(request, *args, **kwargs)

            # Check if client accepts gzip
            accept_encoding = request.headers.get('accept-encoding', '')
            if 'gzip' not in accept_encoding.lower():
                return response

            # Check response size
            body = b''
            if hasattr(response, 'body'):
                body = response.body

            if len(body) < minimum_size:
                return response

            # Compress
            import gzip
            compressed = gzip.compress(body)

            response.body = compressed
            if hasattr(response, 'headers'):
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Content-Length'] = str(len(compressed))

            return response
        return wrapped

    if view_func:
        return decorator(view_func)
    return decorator


def noindex(view_func: Callable):
    """Decorator to add X-Robots-Tag: noindex."""
    @wraps(view_func)
    async def wrapped(request, *args, **kwargs):
        response = await view_func(request, *args, **kwargs)
        if hasattr(response, 'headers'):
            response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        return response
    return wrapped


def nosniff(view_func: Callable):
    """Decorator to add X-Content-Type-Options: nosniff."""
    @wraps(view_func)
    async def wrapped(request, *args, **kwargs):
        response = await view_func(request, *args, **kwargs)
        if hasattr(response, 'headers'):
            response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    return wrapped


# Import asyncio for async checks
import asyncio
