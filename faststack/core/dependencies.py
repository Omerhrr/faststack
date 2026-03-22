"""
FastStack Core Dependencies

Provides dependency injection helpers for authentication, sessions, etc.
"""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlmodel import Session

from faststack.database import get_session
from faststack.auth.models import User


# Security schemes
http_basic = HTTPBasic(auto_error=False)


async def get_current_user(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """
    Get the currently authenticated user.

    Raises:
        HTTPException: If user is not authenticated

    Returns:
        User: The authenticated user
    """
    # Check session-based auth first
    user_id = request.session.get("user_id")
    if user_id:
        user = session.get(User, user_id)
        if user:
            return user

    # Fall back to basic auth (for API access)
    credentials = await http_basic(request)
    if credentials:
        from faststack.auth.utils import verify_password

        user = session.exec(
            User.__table__.select().where(
                User.email == credentials.username
            )
        ).first()

        if user and verify_password(credentials.password, user.password_hash):
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> User | None:
    """
    Get the current user if authenticated, otherwise return None.

    Returns:
        User | None: The authenticated user or None
    """
    user_id = request.session.get("user_id")
    if user_id:
        return session.get(User, user_id)
    return None


async def get_admin_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get the current user and verify they are an admin.

    Raises:
        HTTPException: If user is not an admin

    Returns:
        User: The authenticated admin user
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]
DBSession = Annotated[Session, Depends(get_session)]
