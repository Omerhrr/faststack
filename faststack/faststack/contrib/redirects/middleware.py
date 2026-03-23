"""
Redirect middleware for automatic URL redirection.
"""

from typing import Any, Optional
from starlette.requests import Request
from starlette.responses import RedirectResponse

from .models import Redirect


class RedirectFallbackMiddleware:
    """
    Middleware that catches 404s and checks for redirects.

    This middleware intercepts 404 responses and checks if there's
    a matching redirect in the database.

    Example:
        app = FastStack()
        app.add_middleware(RedirectFallbackMiddleware)

    Note:
        This should be added after the main routing middleware but
        before any error handling middleware.
    """

    def __init__(self, app: Any, db_attr: str = 'db'):
        """
        Initialize RedirectFallbackMiddleware.

        Args:
            app: ASGI application
            db_attr: Attribute name for database on app.state
        """
        self.app = app
        self.db_attr = db_attr
        self._cache = {}  # Simple in-memory cache

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # Store messages for replay
        messages = []
        status_code = None

        async def send_wrapper(message):
            nonlocal status_code
            messages.append(message)

            if message['type'] == 'http.response.start':
                status_code = message['status']

            await send(message)

        # Try main app
        await self.app(scope, receive, send_wrapper)

        # If 404, check for redirect
        if status_code == 404 and scope['method'] in ('GET', 'HEAD', 'POST'):
            redirect = await self._get_redirect(scope)

            if redirect:
                # Increment hit counter
                db = self._get_db(scope)
                if db:
                    await redirect.increment_hits(db)

                # Create redirect response
                response = RedirectResponse(
                    url=redirect.new_path,
                    status_code=redirect.status_code
                )
                await response(scope, receive, send)

    async def _get_redirect(self, scope: dict) -> Optional[Redirect]:
        """Get redirect for current path."""
        request = Request(scope)
        path = request.url.path

        # Check cache first
        if path in self._cache:
            return self._cache[path]

        # Get database
        db = self._get_db(scope)

        if not db:
            return None

        # Look up redirect
        redirect = await Redirect.get(db, path)

        # Cache result (positive or negative)
        self._cache[path] = redirect

        return redirect

    def _get_db(self, scope: dict) -> Optional[Any]:
        """Get database from app state."""
        app = scope.get('app')
        if app and hasattr(app, 'state'):
            return getattr(app.state, self.db_attr, None)
        return None


class RedirectMiddleware:
    """
    Simplified redirect middleware for pre-defined redirects.

    Use this for redirects without database lookup.

    Example:
        redirects = {
            '/old-page/': '/new-page/',
            '/legacy/': '/modern/',
        }
        app.add_middleware(RedirectMiddleware, redirects=redirects)
    """

    def __init__(self, app: Any, redirects: dict = None):
        """
        Initialize RedirectMiddleware.

        Args:
            app: ASGI application
            redirects: Dictionary mapping old paths to new paths
        """
        self.app = app
        self.redirects = redirects or {}

    def add_redirect(self, old_path: str, new_path: str, permanent: bool = False):
        """Add a redirect."""
        self.redirects[old_path] = (new_path, permanent)

    def remove_redirect(self, old_path: str):
        """Remove a redirect."""
        self.redirects.pop(old_path, None)

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # Check for redirect
        request = Request(scope)
        path = request.url.path

        if path in self.redirects:
            redirect = self.redirects[path]

            if isinstance(redirect, tuple):
                new_path, permanent = redirect
            else:
                new_path = redirect
                permanent = False

            status_code = 301 if permanent else 302
            response = RedirectResponse(url=new_path, status_code=status_code)
            await response(scope, receive, send)
            return

        # No redirect, continue to app
        await self.app(scope, receive, send)


class RedirectAdmin:
    """
    Admin configuration for Redirect model.

    Example:
        from faststack.contrib.admin import admin
        from faststack.contrib.redirects import RedirectAdmin

        admin.register(Redirect, RedirectAdmin)
    """

    list_display = ['old_path', 'new_path', 'is_permanent', 'hits']
    list_filter = ['is_permanent']
    search_fields = ['old_path', 'new_path']
    ordering = ['old_path']
