"""
Messages API - Django-like convenience functions.

Example:
    from faststack.core.messages import messages

    messages.success(request, "Profile updated!")
    messages.error(request, "Something went wrong.")
"""

from typing import Any, Optional
from .constants import DEBUG, INFO, SUCCESS, WARNING, ERROR
from .storage import MessageStorage

# Global storage instances per request
_storages: dict = {}


def _get_storage(request: Any) -> MessageStorage:
    """Get or create message storage for request."""
    if request is None:
        # Return a temporary storage
        return MessageStorage(None)

    # Use request id as key
    request_id = id(request)
    if request_id not in _storages:
        _storages[request_id] = MessageStorage(request)

    return _storages[request_id]


def add_message(
    request: Any,
    level: int,
    message: str,
    extra_tags: str = '',
    fail_silently: bool = False
) -> Optional[Any]:
    """
    Add a message with the given level.

    Args:
        request: The request object
        level: Message level (DEBUG, INFO, SUCCESS, WARNING, ERROR)
        message: Message text
        extra_tags: Additional CSS tags
        fail_silently: Don't raise errors if storage is unavailable

    Returns:
        The created Message object
    """
    storage = _get_storage(request)
    return storage.add(level, message, extra_tags)


def debug(request: Any, message: str, extra_tags: str = '', fail_silently: bool = False):
    """Add a debug message."""
    return add_message(request, DEBUG, message, extra_tags, fail_silently)


def info(request: Any, message: str, extra_tags: str = '', fail_silently: bool = False):
    """Add an info message."""
    return add_message(request, INFO, message, extra_tags, fail_silently)


def success(request: Any, message: str, extra_tags: str = '', fail_silently: bool = False):
    """Add a success message."""
    return add_message(request, SUCCESS, message, extra_tags, fail_silently)


def warning(request: Any, message: str, extra_tags: str = '', fail_silently: bool = False):
    """Add a warning message."""
    return add_message(request, WARNING, message, extra_tags, fail_silently)


def error(request: Any, message: str, extra_tags: str = '', fail_silently: bool = False):
    """Add an error message."""
    return add_message(request, ERROR, message, extra_tags, fail_silently)


def get_messages(request: Any):
    """Get all messages for a request."""
    storage = _get_storage(request)
    return storage.get_messages()


def clear_messages(request: Any):
    """Clear all messages for a request."""
    storage = _get_storage(request)
    storage.clear()
    if id(request) in _storages:
        del _storages[id(request)]


class Messages:
    """
    Messages namespace for easy access.

    Usage:
        from faststack.core.messages import messages

        messages.success(request, "Done!")
        messages.error(request, "Failed!")

        # In template/views
        for msg in messages.get_messages(request):
            print(msg)
    """

    @staticmethod
    def add(request, level, message, extra_tags='', fail_silently=False):
        return add_message(request, level, message, extra_tags, fail_silently)

    @staticmethod
    def debug(request, message, extra_tags='', fail_silently=False):
        return debug(request, message, extra_tags, fail_silently)

    @staticmethod
    def info(request, message, extra_tags='', fail_silently=False):
        return info(request, message, extra_tags, fail_silently)

    @staticmethod
    def success(request, message, extra_tags='', fail_silently=False):
        return success(request, message, extra_tags, fail_silently)

    @staticmethod
    def warning(request, message, extra_tags='', fail_silently=False):
        return warning(request, message, extra_tags, fail_silently)

    @staticmethod
    def error(request, message, extra_tags='', fail_silently=False):
        return error(request, message, extra_tags, fail_silently)

    @staticmethod
    def get_messages(request):
        return get_messages(request)

    @staticmethod
    def clear(request):
        return clear_messages(request)


# Create singleton instance
messages = Messages()
