"""
FastStack Messages Framework

Provides a Django-like messages framework for flash messages.

Example:
    from faststack.core.messages import messages

    # Add messages
    messages.success(request, "Profile updated successfully!")
    messages.error(request, "Something went wrong.")
    messages.warning(request, "Your account expires in 7 days.")
    messages.info(request, "New features available!")

    # In template
    {% for message in messages %}
        <div class="alert alert-{{ message.level_tag }}">
            {{ message }}
        </div>
    {% endfor %}
"""

from .api import success, error, warning, info, debug
from .storage import MessageStorage, CookieStorage, SessionStorage
from .constants import (
    DEBUG, INFO, SUCCESS, WARNING, ERROR,
    DEFAULT_LEVELS, DEFAULT_TAGS
)
from .middleware import MessageMiddleware

__all__ = [
    # API functions
    'success', 'error', 'warning', 'info', 'debug',
    # Storage
    'MessageStorage', 'CookieStorage', 'SessionStorage',
    # Constants
    'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR',
    'DEFAULT_LEVELS', 'DEFAULT_TAGS',
    # Middleware
    'MessageMiddleware',
]
