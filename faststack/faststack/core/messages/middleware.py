"""
Message middleware for automatic message handling.
"""

from typing import Any, Callable
from .storage import FallbackStorage


class MessageMiddleware:
    """
    Middleware for handling flash messages.

    This middleware:
    1. Loads messages from storage at the start of each request
    2. Saves messages to storage at the end of each request

    Example:
        app = FastStack()
        app.add_middleware(MessageMiddleware)
    """

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # Create request-like object for message storage
        from starlette.requests import Request
        request = Request(scope, receive)

        # Initialize message storage
        storage = FallbackStorage(request)
        scope['messages'] = storage

        # Process request
        response_started = False
        response_obj = None

        async def send_wrapper(message: dict):
            nonlocal response_started, response_obj

            if message['type'] == 'http.response.start':
                response_started = True
                # Create response object for storage
                from starlette.responses import Response

            if message['type'] == 'http.response.body':
                # Update messages in storage
                if not response_started:
                    # Store messages for next request
                    storage.update(response_obj)

            await send(message)

        await self.app(scope, receive, send_wrapper)


class MessageMiddlewareASGI:
    """
    ASGI3 message middleware.

    Example:
        app = FastStack()
        app.add_middleware(MessageMiddlewareASGI)
    """

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable):
        await self.app(scope, receive, send)


def get_messages(request: Any):
    """
    Get messages from request.

    Args:
        request: Request object

    Returns:
        List of messages
    """
    if hasattr(request, 'scope') and 'messages' in request.scope:
        return list(request.scope['messages'])

    from .api import get_messages as _get_messages
    return _get_messages(request)
