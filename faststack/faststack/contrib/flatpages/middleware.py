"""
FlatPage middleware.
"""

from typing import Any, Callable
from .models import FlatPage
from .views import _render_flatpage


class FlatpageFallbackMiddleware:
    """
    Middleware that catches 404s and tries to find a flatpage.

    This middleware intercepts 404 responses and attempts to find
    a matching flatpage before returning the 404 error.

    Example:
        app = FastStack()
        app.add_middleware(FlatpageFallbackMiddleware)

    Note:
        This middleware should be added last, so it can catch all 404s.
    """

    def __init__(self, app: Any, db_attr: str = 'db'):
        """
        Initialize FlatpageFallbackMiddleware.

        Args:
            app: ASGI application
            db_attr: Attribute name for database on app.state
        """
        self.app = app
        self.db_attr = db_attr

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # Store messages for replay
        messages = []
        response_started = False
        status_code = None

        async def send_wrapper(message):
            nonlocal response_started, status_code
            messages.append(message)

            if message['type'] == 'http.response.start':
                status_code = message['status']
                response_started = True

            await send(message)

        # Try main app
        await self.app(scope, receive, send_wrapper)

        # If 404, try flatpage
        if status_code == 404 and scope['method'] == 'GET':
            from starlette.requests import Request
            from starlette.responses import HTMLResponse

            request = Request(scope, receive)
            url = request.url.path

            # Normalize URL
            if not url.endswith('/'):
                url += '/'

            # Get database
            app = scope.get('app')
            db = None
            if app and hasattr(app, 'state'):
                db = getattr(app.state, self.db_attr, None)

            if db:
                try:
                    page = await FlatPage.get(db, url)

                    if page:
                        # Check registration requirement
                        if page.registration_required:
                            user = scope.get('user')
                            if not user or not getattr(user, 'is_authenticated', False):
                                from starlette.responses import RedirectResponse
                                response = RedirectResponse(url='/login/', status_code=302)
                                await response(scope, receive, send)
                                return

                        # Render flatpage
                        html = _render_flatpage(page, {'flatpage': page, 'request': request})

                        # Send new response
                        await send({
                            'type': 'http.response.start',
                            'status': 200,
                            'headers': [
                                [b'content-type', b'text/html; charset=utf-8'],
                            ]
                        })
                        await send({
                            'type': 'http.response.body',
                            'body': html.encode('utf-8'),
                        })
                except Exception:
                    # If any error, let 404 stand
                    pass
