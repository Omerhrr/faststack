"""
FastStack Internationalization (i18n) Module

Provides comprehensive i18n support similar to Django.

Features:
- Translation functions (gettext, ngettext, etc.)
- Language detection and activation
- Locale middleware
- Template tags for Jinja2
- Message file management
- Timezone support

Example:
    from faststack.core.i18n import gettext as _, ngettext
    
    # Basic translation
    message = _("Welcome to our site")
    
    # Pluralization
    count = len(items)
    message = ngettext(
        "You have %(count)d message",
        "You have %(count)d messages",
        count
    ) % {"count": count}
    
    # Activate language
    from faststack.core.i18n import activate
    activate('de')  # Switch to German
"""

from faststack.core.i18n.translation import (
    gettext,
    ngettext,
    pgettext,
    npgettext,
    activate,
    deactivate,
    get_language,
    get_language_info,
    LANGUAGE_SESSION_KEY,
)
from faststack.core.i18n.middleware import LocaleMiddleware
from faststack.core.i18n.utils import (
    get_supported_language_variant,
    check_for_language,
)

# Common aliases
_ = gettext

__all__ = [
    # Translation functions
    "gettext",
    "ngettext",
    "pgettext",
    "npgettext",
    "_",
    # Language management
    "activate",
    "deactivate",
    "get_language",
    "get_language_info",
    "LANGUAGE_SESSION_KEY",
    # Middleware
    "LocaleMiddleware",
    # Utilities
    "get_supported_language_variant",
    "check_for_language",
]
