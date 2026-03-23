"""
Locale Middleware

Middleware for automatic language detection and activation.
"""

import re
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from faststack.faststack.core.i18n.translation import (
    activate,
    deactivate,
    get_language,
    LANGUAGE_SESSION_KEY,
)


class LocaleMiddleware(BaseHTTPMiddleware):
    """
    Middleware that determines the user's language preference.
    
    Language is detected in this order:
    1. Language prefix in URL (e.g., /en/about/, /de/ueber-uns/)
    2. Language stored in session
    3. Language cookie
    4. Accept-Language HTTP header
    5. Default language from settings
    
    Example settings:
        LANGUAGE_CODE = 'en'
        LANGUAGES = [
            ('en', 'English'),
            ('de', 'German'),
            ('fr', 'French'),
        ]
        LANGUAGE_COOKIE_NAME = 'language'
        LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 365  # 1 year
    """
    
    # URL prefix pattern for language
    LANGUAGE_PREFIX_PATTERN = re.compile(r'^/(\w{2}(?:[-_]\w{2})?)(/|$)')
    
    def __init__(
        self,
        app: ASGIApp,
        default_language: str = 'en',
        supported_languages: list[str] | None = None,
        language_cookie_name: str = 'language',
        language_cookie_age: int = 60 * 60 * 24 * 365,
        language_cookie_domain: str | None = None,
        language_cookie_path: str = '/',
        language_cookie_secure: bool = False,
        language_cookie_httponly: bool = True,
        language_cookie_samesite: str = 'lax',
        use_session: bool = True,
        use_accept_language: bool = True,
    ):
        """
        Initialize the locale middleware.
        
        Args:
            app: ASGI application
            default_language: Default language code
            supported_languages: List of supported language codes
            language_cookie_name: Cookie name for language preference
            language_cookie_age: Cookie max age in seconds
            language_cookie_domain: Cookie domain
            language_cookie_path: Cookie path
            language_cookie_secure: Whether cookie requires HTTPS
            language_cookie_httponly: Whether cookie is HTTP-only
            language_cookie_samesite: SameSite attribute
            use_session: Whether to check session for language
            use_accept_language: Whether to check Accept-Language header
        """
        super().__init__(app)
        self.default_language = default_language
        self.supported_languages = supported_languages or [default_language]
        self.language_cookie_name = language_cookie_name
        self.language_cookie_age = language_cookie_age
        self.language_cookie_domain = language_cookie_domain
        self.language_cookie_path = language_cookie_path
        self.language_cookie_secure = language_cookie_secure
        self.language_cookie_httponly = language_cookie_httponly
        self.language_cookie_samesite = language_cookie_samesite
        self.use_session = use_session
        self.use_accept_language = use_accept_language
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and determine language.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
        
        Returns:
            Response
        """
        # Try to get language from various sources
        language = None
        language_from_path = False
        
        # 1. Check URL prefix
        language, language_from_path = self._get_language_from_path(request)
        
        # 2. Check session
        if language is None and self.use_session:
            language = self._get_language_from_session(request)
        
        # 3. Check cookie
        if language is None:
            language = self._get_language_from_cookie(request)
        
        # 4. Check Accept-Language header
        if language is None and self.use_accept_language:
            language = self._get_language_from_header(request)
        
        # 5. Fall back to default
        if language is None:
            language = self.default_language
        
        # Activate the language
        activate(language)
        
        # Store in request for easy access
        request.state.language = language
        
        # Process request
        response = await call_next(request)
        
        # Set language cookie if it was determined from path (new preference)
        if language_from_path:
            self._set_language_cookie(response, language)
        
        # Deactivate after request
        deactivate()
        
        return response
    
    def _get_language_from_path(self, request: Request) -> tuple[str | None, bool]:
        """
        Extract language from URL path.
        
        Returns:
            Tuple of (language, from_path)
        """
        path = request.url.path
        match = self.LANGUAGE_PREFIX_PATTERN.match(path)
        
        if match:
            lang_code = match.group(1)
            if lang_code in self.supported_languages:
                return lang_code, True
        
        return None, False
    
    def _get_language_from_session(self, request: Request) -> str | None:
        """Get language from session."""
        session = getattr(request, 'session', None)
        if session:
            lang_code = session.get(LANGUAGE_SESSION_KEY)
            if lang_code in self.supported_languages:
                return lang_code
        return None
    
    def _get_language_from_cookie(self, request: Request) -> str | None:
        """Get language from cookie."""
        lang_code = request.cookies.get(self.language_cookie_name)
        if lang_code and lang_code in self.supported_languages:
            return lang_code
        return None
    
    def _get_language_from_header(self, request: Request) -> str | None:
        """
        Get language from Accept-Language header.
        
        Parses the header and finds the best matching supported language.
        """
        accept_language = request.headers.get('Accept-Language', '')
        if not accept_language:
            return None
        
        # Parse Accept-Language header
        languages = []
        for part in accept_language.split(','):
            part = part.strip()
            if not part:
                continue
            
            # Parse language and quality
            if ';' in part:
                lang, q = part.split(';', 1)
                try:
                    q = float(q.strip().split('=')[1])
                except (IndexError, ValueError):
                    q = 1.0
            else:
                lang = part
                q = 1.0
            
            languages.append((lang.strip().lower(), q))
        
        # Sort by quality (highest first)
        languages.sort(key=lambda x: -x[1])
        
        # Find best match
        for lang, _ in languages:
            # Try exact match
            if lang in self.supported_languages:
                return lang
            
            # Try primary language (e.g., 'en' from 'en-US')
            primary = lang.split('-')[0]
            if primary in self.supported_languages:
                return primary
        
        return None
    
    def _set_language_cookie(self, response: Response, language: str) -> None:
        """Set the language cookie on the response."""
        response.set_cookie(
            key=self.language_cookie_name,
            value=language,
            max_age=self.language_cookie_age,
            domain=self.language_cookie_domain,
            path=self.language_cookie_path,
            secure=self.language_cookie_secure,
            httponly=self.language_cookie_httponly,
            samesite=self.language_cookie_samesite,
        )


def get_language_from_request(request: Request) -> str:
    """
    Get the active language from a request.
    
    Args:
        request: FastAPI request
    
    Returns:
        Language code
    """
    # Check if middleware set it
    if hasattr(request.state, 'language'):
        return request.state.language
    
    # Fall back to settings
    from faststack.config import settings
    return getattr(settings, 'LANGUAGE_CODE', 'en')
