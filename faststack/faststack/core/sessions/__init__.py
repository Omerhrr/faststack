"""
FastStack Session Backends

Multiple session storage backends like Django.

Example:
    from faststack.core.sessions import SessionMiddleware

    # In your app
    app = FastStack()
    app.add_middleware(SessionMiddleware, backend='redis')

    # In views
    request.session['user_id'] = 123
    request.session.get('user_id')
"""

from .backends import (
    SessionBase,
    SessionStore,
    DatabaseSessionStore,
    RedisSessionStore,
    CookieSessionStore,
    FileSessionStore,
    CacheSessionStore,
)
from .middleware import SessionMiddleware
from .models import Session

__all__ = [
    'SessionBase',
    'SessionStore',
    'DatabaseSessionStore',
    'RedisSessionStore',
    'CookieSessionStore',
    'FileSessionStore',
    'CacheSessionStore',
    'SessionMiddleware',
    'Session',
]
