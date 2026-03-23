"""
FastStack Session Middleware

Provides secure session management using Starlette's session middleware.
"""

import json
import time
from typing import Any, Callable
from starlette.middleware.sessions import SessionMiddleware as StarletteSessionMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send, Message

from faststack.config import settings


class SessionMiddleware:
    """
    Wrapper around Starlette's SessionMiddleware with FastStack defaults.
    
    Provides secure, signed session cookies with configurable settings.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        secret_key: str | None = None,
        session_cookie: str | None = None,
        max_age: int | None = None,
        same_site: str = "lax",
        https_only: bool = False,
    ):
        """
        Initialize session middleware.
        
        Args:
            app: ASGI application
            secret_key: Secret key for signing (default: from settings)
            session_cookie: Cookie name (default: from settings)
            max_age: Session max age in seconds (default: from settings)
            same_site: SameSite cookie attribute
            https_only: If True, set secure flag on cookie
        """
        self.app = app
        self.secret_key = secret_key or settings.SECRET_KEY
        self.session_cookie = session_cookie or settings.SESSION_COOKIE_NAME
        self.max_age = max_age or settings.SESSION_MAX_AGE
        self.same_site = same_site
        self.https_only = https_only or settings.SESSION_COOKIE_SECURE
        
        # Create the actual middleware
        self.middleware = StarletteSessionMiddleware(
            app,
            secret_key=self.secret_key,
            session_cookie=self.session_cookie,
            max_age=self.max_age,
            same_site=self.same_site,
            https_only=self.https_only,
        )
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the request through session middleware."""
        await self.middleware(scope, receive, send)


class SessionData:
    """
    Helper class for accessing session data with defaults.
    
    Usage:
        session = SessionData(request)
        user_id = session.get('user_id')
        session.set('theme', 'dark')
    """
    
    def __init__(self, request: Request):
        """Initialize with a request object."""
        self.request = request
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the session."""
        return self.request.session.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the session."""
        self.request.session[key] = value
    
    def delete(self, key: str) -> None:
        """Delete a value from the session."""
        self.request.session.pop(key, None)
    
    def clear(self) -> None:
        """Clear all session data."""
        self.request.session.clear()
    
    def has(self, key: str) -> bool:
        """Check if a key exists in the session."""
        return key in self.request.session
    
    def keys(self) -> list[str]:
        """Get all session keys."""
        return list(self.request.session.keys())
    
    def items(self) -> list[tuple[str, Any]]:
        """Get all session items."""
        return list(self.request.session.items())
    
    def flash(self, message: str, category: str = "info") -> None:
        """
        Add a flash message to the session.
        
        Args:
            message: Flash message text
            category: Message category (info, success, warning, error)
        """
        flashes = self.get("_flashes", [])
        flashes.append({"message": message, "category": category, "time": time.time()})
        self.set("_flashes", flashes)
    
    def get_flashes(self) -> list[dict[str, Any]]:
        """
        Get and clear all flash messages.
        
        Returns:
            List of flash message dicts
        """
        flashes = self.get("_flashes", [])
        self.delete("_flashes")
        return flashes
    
    def login(self, user_id: int, **extra: Any) -> None:
        """
        Set up session for a logged-in user.
        
        Args:
            user_id: User's ID
            **extra: Additional session data
        """
        self.set("user_id", user_id)
        self.set("authenticated", True)
        self.set("login_time", time.time())
        for key, value in extra.items():
            self.set(key, value)
    
    def logout(self) -> None:
        """Clear session data on logout."""
        self.clear()
    
    def is_authenticated(self) -> bool:
        """Check if the session has an authenticated user."""
        return self.get("authenticated", False) and self.get("user_id") is not None
    
    @property
    def user_id(self) -> int | None:
        """Get the authenticated user's ID."""
        return self.get("user_id")


def get_session(request: Request) -> SessionData:
    """
    Get a SessionData helper for a request.
    
    Args:
        request: Starlette request object
    
    Returns:
        SessionData instance
    """
    return SessionData(request)
