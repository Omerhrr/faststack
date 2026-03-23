"""
FastStack Messages API

Provides the main API functions for adding and retrieving messages.
These functions are designed to be Django-compatible but async-first.

Usage:
    from faststack.contrib.messages import add_message, success, get_messages

    # Add a message
    add_message(request, INFO, "Welcome back!")

    # Use shorthand functions
    success(request, "Profile updated successfully!")
    error(request, "Failed to save changes.")

    # Get all messages
    messages = get_messages(request)
    for msg in messages:
        print(f"{msg.level_tag}: {msg.message}")
"""

from typing import TYPE_CHECKING

from starlette.requests import Request

from faststack.contrib.messages.constants import DEBUG, ERROR, INFO, SUCCESS, WARNING
from faststack.contrib.messages.storage import BaseStorage, FallbackStorage, Message

if TYPE_CHECKING:
    from faststack.contrib.messages.storage import SessionStorage, CookieStorage


def get_storage(request: Request) -> BaseStorage:
    """
    Get the message storage for a request.

    Uses FallbackStorage by default, which tries cookie storage
    first and falls back to session storage if needed.

    Args:
        request: Starlette request object

    Returns:
        Message storage backend

    Example:
        storage = get_storage(request)
        storage.add(INFO, "Hello!")
    """
    # Check if storage is already attached to request
    if hasattr(request, "_messages_storage"):
        return request._messages_storage

    # Create default storage
    storage = FallbackStorage(request)
    request._messages_storage = storage
    return storage


def add_message(
    request: Request,
    level: int,
    message: str,
    extra_tags: str = "",
) -> None:
    """
    Add a message to the request.

    The message will be stored and can be retrieved on the next request
    or the current one if not yet displayed.

    Args:
        request: Starlette request object
        level: Message level (DEBUG, INFO, SUCCESS, WARNING, ERROR)
        message: The message text
        extra_tags: Extra CSS tags for styling

    Example:
        from faststack.contrib.messages.constants import SUCCESS
        add_message(request, SUCCESS, "Your changes have been saved.", "alert alert-success")
    """
    storage = get_storage(request)
    storage.add(level, message, extra_tags)


def debug(request: Request, message: str, extra_tags: str = "") -> None:
    """
    Add a DEBUG level message.

    Debug messages are typically not shown in production.

    Args:
        request: Starlette request object
        message: The message text
        extra_tags: Extra CSS tags

    Example:
        debug(request, "Processing form data: {...}")
    """
    add_message(request, DEBUG, message, extra_tags)


def info(request: Request, message: str, extra_tags: str = "") -> None:
    """
    Add an INFO level message.

    Info messages provide general information to the user.

    Args:
        request: Starlette request object
        message: The message text
        extra_tags: Extra CSS tags

    Example:
        info(request, "Your password will expire in 7 days.")
    """
    add_message(request, INFO, message, extra_tags)


def success(request: Request, message: str, extra_tags: str = "") -> None:
    """
    Add a SUCCESS level message.

    Success messages indicate that an action completed successfully.

    Args:
        request: Starlette request object
        message: The message text
        extra_tags: Extra CSS tags

    Example:
        success(request, "Your profile has been updated.")
    """
    add_message(request, SUCCESS, message, extra_tags)


def warning(request: Request, message: str, extra_tags: str = "") -> None:
    """
    Add a WARNING level message.

    Warning messages alert the user to potential issues.

    Args:
        request: Starlette request object
        message: The message text
        extra_tags: Extra CSS tags

    Example:
        warning(request, "Your session will expire in 5 minutes.")
    """
    add_message(request, WARNING, message, extra_tags)


def error(request: Request, message: str, extra_tags: str = "") -> None:
    """
    Add an ERROR level message.

    Error messages indicate that something went wrong.

    Args:
        request: Starlette request object
        message: The message text
        extra_tags: Extra CSS tags

    Example:
        error(request, "Failed to process payment. Please try again.")
    """
    add_message(request, ERROR, message, extra_tags)


def get_messages(request: Request) -> list[Message]:
    """
    Get all messages and mark them as read.

    Retrieves all stored messages for the request. After this call,
    the messages are considered "read" and will be cleared from storage.

    Args:
        request: Starlette request object

    Returns:
        List of Message objects

    Example:
        messages = get_messages(request)
        for msg in messages:
            print(f"[{msg.level_tag}] {msg.message}")
    """
    storage = get_storage(request)
    return storage.get_messages()


def get_level(request: Request) -> int:
    """
    Get the minimum message level.

    Messages below this level will not be stored.

    Args:
        request: Starlette request object

    Returns:
        Minimum message level integer

    Example:
        level = get_level(request)
        if level <= DEBUG:
            # Debug messages are enabled
            pass
    """
    storage = get_storage(request)
    return storage.get_level()


def set_level(request: Request, level: int | None) -> None:
    """
    Set the minimum message level.

    Messages below this level will not be stored.
    Set to None to reset to default (INFO).

    Args:
        request: Starlette request object
        level: New minimum level or None for default

    Example:
        # Only show warnings and errors
        set_level(request, WARNING)

        # Reset to default
        set_level(request, None)
    """
    storage = get_storage(request)
    storage.set_level(level)


def _get_request_messages(request: Request) -> list[Message]:
    """
    Internal function to get messages without marking as read.

    Used by templates to access messages.

    Args:
        request: Starlette request object

    Returns:
        List of Message objects
    """
    storage = get_storage(request)
    return list(storage)


def _mark_messages_read(request: Request) -> None:
    """
    Internal function to mark messages as read.

    Called after messages are retrieved for display.

    Args:
        request: Starlette request object
    """
    storage = get_storage(request)
    # Clear stored messages by storing empty list
    storage._queued_messages = []
