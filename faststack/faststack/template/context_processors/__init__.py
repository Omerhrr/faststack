"""
FastStack Context Processors - Global template context.

Example:
    from faststack.template.context_processors import (
        request,
        user,
        messages,
        static,
        media,
        csrf
    )

    # In app config
    CONTEXT_PROCESSORS = [
        'faststack.template.context_processors.request',
        'faststack.template.context_processors.user',
        'faststack.template.context_processors.messages',
        'faststack.template.context_processors.static',
    ]
"""

from typing import Any, Dict, Optional
import os
import secrets


def request(request: Any) -> Dict[str, Any]:
    """
    Add request to template context.

    Returns:
        {'request': request}
    """
    return {'request': request}


def user(request: Any) -> Dict[str, Any]:
    """
    Add user to template context.

    Returns:
        {'user': user, 'user_permissions': [...]}
    """
    user = getattr(request, 'user', None)

    if user is None:
        from ...auth.backends import AnonymousUser
        user = AnonymousUser()

    return {
        'user': user,
        'user_permissions': getattr(user, 'get_all_permissions', lambda: set())(),
        'perms': PermissionWrapper(user),
    }


def messages(request: Any) -> Dict[str, Any]:
    """
    Add messages to template context.

    Returns:
        {'messages': [...]}
    """
    from ...core.messages import get_messages

    return {
        'messages': get_messages(request),
        'DEFAULT_MESSAGE_LEVELS': {
            'DEBUG': 10,
            'INFO': 20,
            'SUCCESS': 25,
            'WARNING': 30,
            'ERROR': 40,
        }
    }


def static(request: Any) -> Dict[str, Any]:
    """
    Add static file helpers to template context.

    Returns:
        {'static': static_url_function, 'STATIC_URL': ...}
    """
    static_url = getattr(request.app, 'static_url', '/static/') if hasattr(request, 'app') else '/static/'

    def static_url_func(path: str) -> str:
        """Get full URL for a static file."""
        return f"{static_url.rstrip('/')}/{path.lstrip('/')}"

    return {
        'static': static_url_func,
        'STATIC_URL': static_url,
    }


def media(request: Any) -> Dict[str, Any]:
    """
    Add media file helpers to template context.

    Returns:
        {'media': media_url_function, 'MEDIA_URL': ...}
    """
    media_url = getattr(request.app, 'media_url', '/media/') if hasattr(request, 'app') else '/media/'

    def media_url_func(path: str) -> str:
        """Get full URL for a media file."""
        return f"{media_url.rstrip('/')}/{path.lstrip('/')}"

    return {
        'media': media_url_func,
        'MEDIA_URL': media_url,
    }


def csrf(request: Any) -> Dict[str, Any]:
    """
    Add CSRF token to template context.

    Returns:
        {'csrf_token': token, 'csrf_token_input': html_input}
    """
    # Get or generate CSRF token
    csrf_token = getattr(request, 'csrf_token', None)

    if csrf_token is None:
        # Try to get from session
        session = getattr(request, 'session', {})
        csrf_token = session.get('csrf_token')

        if not csrf_token:
            csrf_token = secrets.token_hex(32)
            if hasattr(session, '__setitem__'):
                session['csrf_token'] = csrf_token

    def csrf_input() -> str:
        """Generate CSRF token hidden input HTML."""
        return f'<input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">'

    return {
        'csrf_token': csrf_token,
        'csrf_token_input': csrf_input,
        'csrf_input': csrf_input,
    }


def debug(request: Any) -> Dict[str, Any]:
    """
    Add debug info to template context.

    Returns:
        {'debug': True/False, 'sql_queries': [...]}
    """
    debug_mode = getattr(request.app, 'debug', False) if hasattr(request, 'app') else False

    context = {
        'debug': debug_mode,
    }

    if debug_mode:
        # Add SQL queries if available
        context['sql_queries'] = getattr(request, 'sql_queries', [])

    return context


def settings(request: Any) -> Dict[str, Any]:
    """
    Add selected settings to template context.

    Returns:
        {'SETTINGS': {...}}
    """
    settings_obj = getattr(request.app, 'settings', {}) if hasattr(request, 'app') else {}

    # Only expose safe settings
    safe_settings = [
        'SITE_NAME',
        'SITE_URL',
        'SITE_DESCRIPTION',
        'CONTACT_EMAIL',
        'SUPPORT_EMAIL',
        'TIME_ZONE',
        'LANGUAGE_CODE',
        'ALLOWED_HOSTS',
    ]

    return {
        'SETTINGS': {
            key: getattr(settings_obj, key, None) if hasattr(settings_obj, key) else settings_obj.get(key)
            for key in safe_settings
            if hasattr(settings_obj, key) or key in settings_obj
        }
    }


def timezone(request: Any) -> Dict[str, Any]:
    """
    Add timezone helpers to template context.

    Returns:
        {'timezone': tz, 'now': datetime, 'today': date}
    """
    from datetime import datetime

    # Get current timezone
    tz = None
    try:
        from zoneinfo import ZoneInfo
        tz_name = 'UTC'  # Default
        if hasattr(request, 'user') and hasattr(request.user, 'timezone'):
            tz_name = request.user.timezone
        tz = ZoneInfo(tz_name)
    except ImportError:
        pass

    now = datetime.now(tz) if tz else datetime.utcnow()
    today = now.date()

    return {
        'timezone': tz,
        'now': now,
        'today': today,
    }


def i18n(request: Any) -> Dict[str, Any]:
    """
    Add i18n helpers to template context.

    Returns:
        {'LANGUAGE_CODE': ..., 'LANGUAGE_BIDI': ..., 'get_current_language': func}
    """
    # Get language from request
    lang_code = 'en'

    # Try from user preference
    if hasattr(request, 'user') and hasattr(request.user, 'language'):
        lang_code = request.user.language

    # Try from Accept-Language header
    elif hasattr(request, 'headers'):
        accept_language = request.headers.get('accept-language', '')
        if accept_language:
            # Parse Accept-Language header
            lang_code = accept_language.split(',')[0].split('-')[0]

    # Try from session
    session = getattr(request, 'session', {})
    if session and 'language' in session:
        lang_code = session['language']

    # Bidi detection (RTL languages)
    rtl_languages = {'ar', 'he', 'fa', 'ur'}
    is_bidi = lang_code in rtl_languages

    return {
        'LANGUAGE_CODE': lang_code,
        'LANGUAGE_BIDI': is_bidi,
        'LANGUAGES': [
            ('en', 'English'),
            ('es', 'Spanish'),
            ('fr', 'French'),
            ('de', 'German'),
            ('zh', 'Chinese'),
            ('ja', 'Japanese'),
            ('ar', 'Arabic'),
        ],
        'get_current_language': lambda: lang_code,
    }


def site(request: Any) -> Dict[str, Any]:
    """
    Add site info to template context.

    Returns:
        {'site': Site object}
    """
    # Try to get current site
    site_obj = None

    try:
        # Would need Site model integration
        pass
    except:
        pass

    # Fallback to request-based site info
    if site_obj is None:
        class Site:
            def __init__(self, request):
                self.domain = request.headers.get('host', 'localhost')
                self.name = self.domain.split(':')[0]

        site_obj = Site(request)

    return {'site': site_obj}


class PermissionWrapper:
    """
    Wrapper for permission checking in templates.

    Example in template:
        {% if perms.blog.add_post %}
            <a href="/blog/new/">Create Post</a>
        {% endif %}

        {% if perms.blog %}
            User has some blog permissions
        {% endif %}
    """

    def __init__(self, user: Any):
        self.user = user
        self._cache = {}

    def __repr__(self) -> str:
        return f"<PermissionWrapper for {self.user}>"

    def __getitem__(self, app_label: str) -> 'AppPermissionWrapper':
        """Get permission wrapper for an app."""
        if app_label not in self._cache:
            self._cache[app_label] = AppPermissionWrapper(self.user, app_label)
        return self._cache[app_label]

    def __contains__(self, perm: str) -> bool:
        """Check if user has a permission."""
        if '.' in perm:
            app_label, codename = perm.split('.', 1)
            return self.user.has_perm(perm) if hasattr(self.user, 'has_perm') else False
        return False


class AppPermissionWrapper:
    """Permission wrapper for a specific app."""

    def __init__(self, user: Any, app_label: str):
        self.user = user
        self.app_label = app_label
        self._cache = {}

    def __repr__(self) -> str:
        return f"<AppPermissionWrapper for {self.app_label}>"

    def __getitem__(self, codename: str) -> bool:
        """Check if user has permission."""
        if codename not in self._cache:
            perm = f"{self.app_label}.{codename}"
            self._cache[codename] = self.user.has_perm(perm) if hasattr(self.user, 'has_perm') else False
        return self._cache[codename]

    def __contains__(self, codename: str) -> bool:
        """Check if user has permission."""
        return self[codename]

    def __bool__(self) -> bool:
        """Check if user has any permissions for this app."""
        # This would check all permissions for the app
        return True


# Built-in context processors list
BUILTIN_CONTEXT_PROCESSORS = [
    request,
    user,
    static,
    csrf,
    messages,
]
