"""
FastStack Core Dependencies

Provides dependency injection helpers for authentication, sessions, etc.
"""

from typing import Annotated, Any, Generator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlmodel import Session, select

from faststack.database import get_engine
from faststack.config import settings


# Security schemes
http_basic = HTTPBasic(auto_error=False)


# Database session dependency - must be a generator for FastAPI Depends
def get_session() -> Generator[Session, None, None]:
    """Get a database session (generator for FastAPI dependency injection)."""
    engine = get_engine()
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()


# Type alias for database session
DBSession = Annotated[Session, Depends(get_session)]


def get_current_user(
    request: Request,
    session: DBSession,
) -> Any:
    """
    Get the currently authenticated user.

    Raises:
        HTTPException: If user is not authenticated

    Returns:
        User: The authenticated user
    """
    from faststack.auth.models import User

    # Check session-based auth first
    user_id = request.session.get("user_id")
    if user_id:
        user = session.get(User, user_id)
        if user:
            return user

    # Fall back to basic auth (for API access)
    credentials = request.headers.get("Authorization")
    if credentials and credentials.startswith("Bearer "):
        # JWT token auth
        token = credentials.replace("Bearer ", "")
        from faststack.auth.jwt import get_jwt_manager
        try:
            jwt_manager = get_jwt_manager()
            token_data = jwt_manager.validate_token(token)
            user = session.get(User, int(token_data.sub))
            if user:
                return user
        except Exception:
            pass

    # Basic auth
    import base64
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth.replace("Basic ", "")).decode()
            email, password = decoded.split(":", 1)
            
            from faststack.auth.utils import verify_password
            user = session.exec(select(User).where(User.email == email)).first()
            
            if user and verify_password(password, user.password_hash):
                return user
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_optional_user(
    request: Request,
    session: DBSession,
) -> Any:
    """
    Get the current user if authenticated, otherwise return None.

    Returns:
        User | None: The authenticated user or None
    """
    from faststack.auth.models import User
    
    user_id = request.session.get("user_id")
    if user_id:
        return session.get(User, user_id)
    return None


def get_admin_user(
    user: Any = Depends(get_current_user),
) -> Any:
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
CurrentUser = Annotated[Any, Depends(get_current_user)]
OptionalUser = Annotated[Any | None, Depends(get_optional_user)]
AdminUser = Annotated[Any, Depends(get_admin_user)]
