"""
FastStack Session Management

Provides session handling utilities using itsdangerous for secure session signing.
"""

import json
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


def login_user(request: Request, user_id: int, **extra: Any) -> None:
    """
    Log in a user by setting session data.

    Args:
        request: Starlette request object
        user_id: User ID to store in session
        **extra: Additional data to store in session
    """
    request.session["user_id"] = user_id
    request.session["authenticated"] = True
    request.session["login_time"] = datetime.utcnow().isoformat()
    request.session.update(extra)


def logout_user(request: Request) -> None:
    """
    Log out the current user by clearing session.

    Args:
        request: Starlette request object
    """
    clear_session(request)


# Global session manager
session_manager = SessionManager()
