"""
FastStack Messages Framework

A Django-compatible, async-first messaging framework for FlashStack.

Provides a temporary message storage system for displaying one-time
notifications to users across requests. Messages are typically used
to confirm actions (like form submissions) or display errors.

Features:
    - Multiple storage backends (session, cookie, fallback)
    - Message levels (DEBUG, INFO, SUCCESS, WARNING, ERROR)
    - Automatic message expiration
    - Django-compatible API

Quick Start:
    from faststack.contrib.messages import (
        add_message, success, error, get_messages,
        MessageMiddleware, SUCCESS, ERROR
    )

    # Add middleware to your app
    app.add_middleware(MessageMiddleware)

    # In your views
    def my_view(request):
        success(request, "Item created successfully!")
        error(request, "Failed to process payment.")

    # In your templates
    {% for message in request.messages %}
        <div class="alert alert-{{ message.level_tag }}">
            {{ message.message }}
        </div>
    {% endfor %}

Storage Backends:
    - SessionStorage: Store messages in session (server-side)
    - CookieStorage: Store messages in signed cookies (client-side)
    - FallbackStorage: Try cookie, fallback to session (recommended)

Message Levels:
    - DEBUG (10): Development/debugging messages
    - INFO (20): General information
    - SUCCESS (25): Successful action confirmation
    - WARNING (30): Warning messages
    - ERROR (40): Error messages

API Functions:
    - add_message(request, level, message, extra_tags=''): Add a message
    - debug(request, message, extra_tags=''): Add DEBUG message
    - info(request, message, extra_tags=''): Add INFO message
    - success(request, message, extra_tags=''): Add SUCCESS message
    - warning(request, message, extra_tags=''): Add WARNING message
    - error(request, message, extra_tags=''): Add ERROR message
    - get_messages(request): Get all messages (marks as read)
    - get_level(request): Get minimum message level
    - set_level(request, level): Set minimum message level

Example Usage:
    # Basic usage
    from faststack.contrib.messages import add_message, SUCCESS

    async def create_item(request):
        # ... create item logic ...
        add_message(request, SUCCESS, "Item created!")
        return RedirectResponse(url="/items")

    # Using shorthand functions
    from faststack.contrib.messages import success, warning

    async def update_settings(request):
        if form.is_valid():
            success(request, "Settings saved!")
        else:
            warning(request, "Please check the form for errors.")

    # With extra CSS tags
    from faststack.contrib.messages import error

    error(request, "Payment failed", extra_tags="alert-danger modal")

    # Getting messages in a view
    from faststack.contrib.messages import get_messages

    async def show_messages(request):
        messages = get_messages(request)
        return JSONResponse({
            "messages": [
                {"level": msg.level_tag, "text": msg.message}
                for msg in messages
            ]
        })

    # Filtering by level
    from faststack.contrib.messages import set_level, WARNING

    # Only show warnings and errors
    set_level(request, WARNING)
"""

# Message levels
from faststack.contrib.messages.constants import (
    DEBUG,
    INFO,
    SUCCESS,
    WARNING,
    ERROR,
    DEFAULT_TAGS,
    DEFAULT_LEVELS,
    MESSAGE_SESSION_KEY,
    MESSAGE_COOKIE_NAME,
    DEFAULT_MESSAGE_LIFETIME,
    MAX_COOKIE_SIZE,
)

# Message class and storage backends
from faststack.contrib.messages.storage import (
    Message,
    BaseStorage,
    SessionStorage,
    CookieStorage,
    FallbackStorage,
)

# API functions
from faststack.contrib.messages.api import (
    get_storage,
    add_message,
    debug,
    info,
    success,
    warning,
    error,
    get_messages,
    get_level,
    set_level,
)

# Middleware
from faststack.contrib.messages.middleware import (
    MessageMiddleware,
    AsyncMessageMiddleware,
    get_request_messages,
)

__all__ = [
    # Constants
    "DEBUG",
    "INFO",
    "SUCCESS",
    "WARNING",
    "ERROR",
    "DEFAULT_TAGS",
    "DEFAULT_LEVELS",
    "MESSAGE_SESSION_KEY",
    "MESSAGE_COOKIE_NAME",
    "DEFAULT_MESSAGE_LIFETIME",
    "MAX_COOKIE_SIZE",
    # Storage
    "Message",
    "BaseStorage",
    "SessionStorage",
    "CookieStorage",
    "FallbackStorage",
    # API
    "get_storage",
    "add_message",
    "debug",
    "info",
    "success",
    "warning",
    "error",
    "get_messages",
    "get_level",
    "set_level",
    # Middleware
    "MessageMiddleware",
    "AsyncMessageMiddleware",
    "get_request_messages",
]

__version__ = "1.0.0"
