"""
FastStack Session Management

Provides session handling utilities using itsdangerous for secure session signing.
Includes protection against session fixation attacks.
"""

import json
import secrets
from datetime import datetime, timedelta
from typing import Any

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from faststack.config import settings


class SessionManager:
    """
    Secure session management using signed cookies.

    Provides:
    - Secure session signing
    - Session creation and validation
    - Flash message support
    - Session regeneration (prevents session fixation)
    """

    def __init__(
        self,
        secret_key: str | None = None,
        max_age: int | None = None,
    ):
        """
        Initialize session manager.

        Args:
            secret_key: Secret key for signing (default: from settings)
            max_age: Session max age in seconds (default: from settings)
        """
        self.secret_key = secret_key or settings.SECRET_KEY
        self.max_age = max_age or settings.SESSION_MAX_AGE
        self.serializer = URLSafeTimedSerializer(self.secret_key)

    def create_session(
        self,
        data: dict[str, Any],
    ) -> str:
        """
        Create a signed session token.

        Args:
            data: Session data to encode

        Returns:
            Signed session token
        """
        # Add timestamp
        data["_created_at"] = datetime.utcnow().isoformat()
        return self.serializer.dumps(data)

    def get_session(
        self,
        token: str,
    ) -> dict[str, Any] | None:
        """
        Decode and validate a session token.

        Args:
            token: Session token to decode

        Returns:
            Session data or None if invalid/expired
        """
        try:
            data = self.serializer.loads(token, max_age=self.max_age)
            return data
        except (BadSignature, SignatureExpired):
            return None

    def get_session_middleware(self) -> SessionMiddleware:
        """
        Get Starlette session middleware.

        Returns:
            Configured SessionMiddleware
        """
        return SessionMiddleware(
            secret_key=self.secret_key,
            session_cookie=settings.SESSION_COOKIE_NAME,
            max_age=self.max_age,
            same_site=settings.SESSION_COOKIE_SAMESITE,
            https_only=settings.SESSION_COOKIE_SECURE,
        )


def get_session_data(request: Request) -> dict[str, Any]:
    """
    Get all session data from request.

    Args:
        request: Starlette request object

    Returns:
        Session data dictionary
    """
    return dict(request.session)


def set_session_data(
    request: Request,
    data: dict[str, Any],
) -> None:
    """
    Set session data on request.

    Args:
        request: Starlette request object
        data: Data to store in session
    """
    request.session.update(data)


def clear_session(request: Request) -> None:
    """
    Clear all session data.

    Args:
        request: Starlette request object
    """
    request.session.clear()


def regenerate_session(request: Request) -> str:
    """
    Regenerate the session ID to prevent session fixation attacks.
    
    This creates a new session while preserving the existing data.
    Should be called after login to prevent session fixation.

    Args:
        request: Starlette request object

    Returns:
        New session identifier
    """
    # Preserve existing session data
    old_data = dict(request.session)
    
    # Clear the session (this effectively creates a new session)
    request.session.clear()
    
    # Generate a new session ID
    new_session_id = secrets.token_urlsafe(32)
    
    # Restore data with new session ID
    old_data["_session_id"] = new_session_id
    old_data["_regenerated_at"] = datetime.utcnow().isoformat()
    
    request.session.update(old_data)
    
    return new_session_id


def get_session_id(request: Request) -> str | None:
    """
    Get the current session ID.

    Args:
        request: Starlette request object

    Returns:
        Session ID or None
    """
    return request.session.get("_session_id")


def flash(
    request: Request,
    message: str,
    category: str = "info",
) -> None:
    """
    Set a flash message to be displayed on the next request.

    Args:
        request: Starlette request object
        message: Flash message text
        category: Message category (info, success, warning, error)
    """
    flashes = request.session.get("_flashes", [])
    flashes.append({"message": message, "category": category})
    request.session["_flashes"] = flashes


def get_flashes(request: Request) -> list[dict[str, str]]:
    """
    Get and clear all flash messages.

    Args:
        request: Starlette request object

    Returns:
        List of flash messages
    """
    flashes = request.session.pop("_flashes", [])
    return flashes


def login_user(
    request: Request,
    user_id: int,
    regenerate: bool = True,
    **extra: Any
) -> None:
    """
    Log in a user by setting session data.
    
    Automatically regenerates session ID to prevent session fixation.

    Args:
        request: Starlette request object
        user_id: User ID to store in session
        regenerate: Whether to regenerate session ID (default: True)
        **extra: Additional data to store in session
    """
    # Regenerate session to prevent session fixation
    if regenerate and settings.SESSION_REGENERATE_ON_LOGIN:
        regenerate_session(request)
    
    request.session["user_id"] = user_id
    request.session["authenticated"] = True
    request.session["login_time"] = datetime.utcnow().isoformat()
    request.session["auth_method"] = "password"  # Track authentication method
    request.session.update(extra)


def logout_user(request: Request) -> None:
    """
    Log out the current user by clearing session.
    
    Completely clears the session and generates a new session ID.

    Args:
        request: Starlette request object
    """
    # Clear all session data
    request.session.clear()
    
    # Generate a new session ID for the anonymous user
    request.session["_session_id"] = secrets.token_urlsafe(32)


def is_authenticated(request: Request) -> bool:
    """
    Check if the current request has an authenticated user.

    Args:
        request: Starlette request object

    Returns:
        True if user is authenticated
    """
    return request.session.get("authenticated", False) and request.session.get("user_id") is not None


def get_current_user_id(request: Request) -> int | None:
    """
    Get the current authenticated user's ID.

    Args:
        request: Starlette request object

    Returns:
        User ID or None if not authenticated
    """
    if not is_authenticated(request):
        return None
    return request.session.get("user_id")


# Global session manager
session_manager = SessionManager()
