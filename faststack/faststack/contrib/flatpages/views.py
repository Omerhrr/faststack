"""
FlatPage views and router.
"""

from typing import Any, Optional
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.exceptions import HTTPException
from starlette.routing import Router

from .models import FlatPage


async def flatpage(request: Request) -> HTMLResponse:
    """
    View for rendering a flatpage.

    Args:
        request: Request object with url path

    Returns:
        HTMLResponse with rendered flatpage
    """
    url = request.path_params.get('url', request.url.path)

    # Ensure URL ends with /
    if not url.endswith('/'):
        url += '/'

    # Get database from app
    db = getattr(request.app.state, 'db', None)

    if db is None:
        raise HTTPException(status_code=404, detail="Page not found")

    # Get flatpage
    page = await FlatPage.get(db, url)

    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")

    # Check if registration required
    if page.registration_required:
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            raise HTTPException(status_code=302, headers={'Location': '/login/'})

    # Render page
    context = {
        'flatpage': page,
        'title': page.title,
        'content': page.content,
    }

    html = _render_flatpage(page, context)
    return HTMLResponse(content=html)


def _render_flatpage(page: FlatPage, context: dict) -> str:
    """Render a flatpage to HTML."""
    template = page.template

    # Check if custom template exists
    # For now, use default template

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{page.title}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; max-width: 800px; }}
            h1 {{ color: #333; }}
            .content {{ line-height: 1.6; }}
        </style>
    </head>
    <body>
        <h1>{page.title}</h1>
        <div class="content">
            {page.content}
        </div>
    </body>
    </html>
    """


# Create router
flatpages_router = Router()


@flatpages_router.route('/{url:path}')
async def flatpage_view(request: Request) -> Response:
    """Catch-all route for flatpages."""
    return await flatpage(request)


class FlatpageFallbackMiddleware:
    """
    Middleware that catches 404s and tries to find a flatpage.

    Example:
        app = FastStack()
        app.add_middleware(FlatpageFallbackMiddleware)
    """

    def __init__(self, app: Any, db_attr: str = 'db'):
        self.app = app
        self.db_attr = db_attr

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # Process request
        response_started = False
        status_code = None

        async def send_wrapper(message):
            nonlocal response_started, status_code

            if message['type'] == 'http.response.start':
                status_code = message['status']
                response_started = True

            await send(message)

        # Try the main app first
        await self.app(scope, receive, send_wrapper)

        # If 404, try flatpage
        if status_code == 404:
            # Create a new request
            from starlette.requests import Request
            request = Request(scope, receive)

            # Get URL
            url = request.url.path
            if not url.endswith('/'):
                url += '/'

            # Get database
            db = getattr(scope.get('app', {}).get('state', {}), self.db_attr, None)

            if db:
                page = await FlatPage.get(db, url)

                if page:
                    # Check if registration required
                    if page.registration_required:
                        user = scope.get('user')
                        if not user or not getattr(user, 'is_authenticated', False):
                            response = Response(status_code=302, headers={'Location': '/login/'})
                            await response(scope, receive, send)
                            return

                    # Render flatpage
                    html = _render_flatpage(page, {'flatpage': page})
                    response = HTMLResponse(content=html)
                    await response(scope, receive, send)
