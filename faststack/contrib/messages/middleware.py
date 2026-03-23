"""
FastStack Messages Middleware

Provides middleware for handling messages across requests.
The middleware:

1. Attaches a messages attribute to the request
2. Updates storage after the response is generated
3. Persists queued messages for the next request

Usage:
    from faststack.contrib.messages.middleware import MessageMiddleware

    app = Starlette()
    app.add_middleware(MessageMiddleware)

    # Or with custom storage
    from faststack.contrib.messages.storage import SessionStorage

    app.add_middleware(MessageMiddleware, storage_class=SessionStorage)
"""

from typing import Callable, Type

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send, Message as ASGIMessage

from faststack.contrib.messages.api import get_storage
from faststack.contrib.messages.storage import BaseStorage, FallbackStorage


class MessageMiddleware:
    """
    Middleware for handling flash messages.

    This middleware:
    - Attaches a message storage to each request
    - Updates the storage after the response is generated
    - Persists queued messages for the next request

    Attributes:
        app: ASGI application
        storage_class: Storage backend class (default: FallbackStorage)

    Example:
        # In your application setup
        from faststack.contrib.messages import MessageMiddleware

        app.add_middleware(MessageMiddleware)

        # In your view
        from faststack.contrib.messages import success

        async def my_view(request):
            success(request, "Item created!")
            return Response("OK")

        # In your template
        {% for message in request.messages %}
            <div class="alert alert-{{ message.level_tag }}">
                {{ message.message }}
            </div>
        {% endfor %}
    """

    def __init__(
        self,
        app: ASGIApp,
        storage_class: Type[BaseStorage] | None = None,
    ):
        """
        Initialize the messages middleware.

        Args:
            app: ASGI application
            storage_class: Storage backend class (default: FallbackStorage)
        """
        self.app = app
        self.storage_class = storage_class or FallbackStorage

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the request through message middleware."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create request object
        request = Request(scope, receive)

        # Attach storage to request
        storage = self.storage_class(request)
        request._messages_storage = storage

        # Add messages property to request
        # This allows template access via request.messages
        @property
        def messages_property(self: Request) -> list:
            """Get messages for this request."""
            return list(get_storage(self))

        # Monkey-patch the request class for this instance
        # In production, you might want to use a custom Request class
        type(request).messages = messages_property

        # Create response wrapper to capture the response
        response_started = False
        response_body: list[bytes] = []

        async def send_wrapper(message: ASGIMessage) -> None:
            nonlocal response_started

            if message["type"] == "http.response.start":
                response_started = True
                # Store headers for later use
                scope["_response_headers"] = message.get("headers", [])
                scope["_response_status"] = message.get("status", 200)
            elif message["type"] == "http.response.body":
                if "body" in message:
                    response_body.append(message["body"])

            await send(message)

        # Process request
        await self.app(scope, receive, send_wrapper)

        # After response, update storage to persist any new messages
        # We need to create a response object to update cookies
        if response_body:
            body = b"".join(response_body)
        else:
            body = b""

        # Create a minimal response for storage update
        response = Response(
            content=body,
            status_code=scope.get("_response_status", 200),
            headers=scope.get("_response_headers", []),
        )

        # Update storage (this sets cookies or session data)
        storage.update(response)

        # If storage added cookies, we need to send them
        # Note: In a real implementation, this would be handled differently
        # For now, cookies are set via session middleware
        if hasattr(response, "set_cookie") and storage._queued_messages:
            # Send Set-Cookie headers if needed
            pass  # CookieStorage handles this via response.set_cookie


class AsyncMessageMiddleware:
    """
    Async-first message middleware.

    This is an alternative implementation that fully supports async
    storage backends. Use this if you have async session backends.

    Example:
        app.add_middleware(AsyncMessageMiddleware)
    """

    def __init__(
        self,
        app: ASGIApp,
        storage_class: Type[BaseStorage] | None = None,
    ):
        """
        Initialize the async messages middleware.

        Args:
            app: ASGI application
            storage_class: Storage backend class (default: FallbackStorage)
        """
        self.app = app
        self.storage_class = storage_class or FallbackStorage

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the request through message middleware."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create request object
        request = Request(scope, receive)

        # Attach storage to request
        storage = self.storage_class(request)
        request._messages_storage = storage

        # Add messages property
        @property
        def messages_property(self: Request) -> list:
            """Get messages for this request."""
            storage = get_storage(self)
            return storage.get_messages()

        type(request).messages = messages_property

        # Track if response has been started
        response_started = False
        response_headers: list[tuple[bytes, bytes]] = []
        response_status = 200

        async def send_wrapper(message: ASGIMessage) -> None:
            nonlocal response_started, response_headers, response_status

            if message["type"] == "http.response.start":
                response_started = True
                response_headers = list(message.get("headers", []))
                response_status = message.get("status", 200)

                # Create response for storage update
                response = Response(
                    content=b"",
                    status_code=response_status,
                    headers=response_headers,
                )

                # Update storage before headers are sent
                storage.update(response)

                # Add any cookies set by storage
                for cookie in response.raw_headers:
                    if cookie[0] == b"set-cookie":
                        response_headers.append(cookie)

                # Update message with new headers
                message = {
                    "type": "http.response.start",
                    "status": response_status,
                    "headers": response_headers,
                }

            await send(message)

        await self.app(scope, receive, send_wrapper)


def get_request_messages(request: Request) -> list:
    """
    Helper function to get messages from a request.

    This is useful for template contexts.

    Args:
        request: Starlette request object

    Returns:
        List of Message objects

    Example:
        # In a view
        context = {
            "messages": get_request_messages(request),
        }
    """
    storage = get_storage(request)
    return storage.get_messages()
