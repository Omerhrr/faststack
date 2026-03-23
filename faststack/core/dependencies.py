"""
FastStack Core Dependencies

Provides dependency injection helpers for authentication, sessions, and permissions.
"""

from typing import Annotated, Any, Generator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from faststack.database import get_engine
from faststack.config import settings


# Security schemes
http_basic = HTTPBasic(auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


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
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
) -> Any:
    """
    Get the currently authenticated user.

    Supports multiple authentication methods:
    1. Session-based auth (cookies)
    2. JWT Bearer token
    3. API token
    4. Basic auth (for testing)

    Raises:
        HTTPException: If user is not authenticated

    Returns:
        User: The authenticated user
    """
    from faststack.auth.models import User

    # 1. Check session-based auth first
    user_id = request.session.get("user_id")
    if user_id:
        user = session.get(User, user_id)
        if user and user.is_active:
            return user

    # 2. Check Bearer token (JWT or API token)
    if credentials:
        token = credentials.credentials
        
        # Check if it's an API token (starts with 'fs_')
        if token.startswith("fs_"):
            from faststack.auth.permissions import validate_api_token
            user = validate_api_token(session, token)
            if user and user.is_active:
                return user
        else:
            # Try JWT token
            try:
                from faststack.auth.jwt import get_jwt_manager
                jwt_manager = get_jwt_manager()
                token_data = jwt_manager.validate_token(token)
                user = session.get(User, int(token_data.sub))
                if user and user.is_active:
                    return user
            except Exception:
                pass

    # 3. Basic auth (for testing/development)
    if settings.DEBUG:
        import base64
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth.replace("Basic ", "")).decode()
                email, password = decoded.split(":", 1)
                
                from faststack.auth.utils import verify_password
                user = session.exec(select(User).where(User.email == email)).first()
                
                if user and user.is_active and verify_password(password, user.password_hash):
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
        user = session.get(User, user_id)
        if user and user.is_active:
            return user
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


def get_superuser(
    user: Any = Depends(get_current_user),
) -> Any:
    """
    Get the current user and verify they are a superuser.

    Raises:
        HTTPException: If user is not a superuser

    Returns:
        User: The authenticated superuser
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return user


def require_permission(permission: str):
    """
    Dependency factory that checks if user has a specific permission.
    
    Args:
        permission: Permission codename (e.g., 'blog.add_post')
    
    Returns:
        Dependency function that raises 403 if permission missing
    
    Example:
        @app.post("/posts/")
        async def create_post(user: User = Depends(require_permission("blog.add_post"))):
            ...
    """
    from faststack.auth.permissions import user_has_permission
    
    def check_permission(
        user: Any = Depends(get_current_user),
        session: DBSession = Depends(get_session),
    ) -> Any:
        if user.is_superuser:
            return user
        
        if user.is_admin and settings.ADMIN_OPTIMISTIC_LOCKING:
            # Admins have all permissions by default in simpler setups
            return user
        
        if not user_has_permission(session, user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return user
    
    return check_permission


def require_any_permission(*permissions: str):
    """
    Dependency factory that checks if user has ANY of the specified permissions.
    """
    from faststack.auth.permissions import user_has_permission
    
    def check_permissions(
        user: Any = Depends(get_current_user),
        session: DBSession = Depends(get_session),
    ) -> Any:
        if user.is_superuser:
            return user
        
        for perm in permissions:
            if user_has_permission(session, user, perm):
                return user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: requires one of {', '.join(permissions)}",
        )
    
    return check_permissions


def require_all_permissions(*permissions: str):
    """
    Dependency factory that checks if user has ALL of the specified permissions.
    """
    from faststack.auth.permissions import user_has_permission
    
    def check_permissions(
        user: Any = Depends(get_current_user),
        session: DBSession = Depends(get_session),
    ) -> Any:
        if user.is_superuser:
            return user
        
        for perm in permissions:
            if not user_has_permission(session, user, perm):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {perm}",
                )
        
        return user
    
    return check_permissions


# Type aliases for dependency injection
CurrentUser = Annotated[Any, Depends(get_current_user)]
OptionalUser = Annotated[Any | None, Depends(get_optional_user)]
AdminUser = Annotated[Any, Depends(get_admin_user)]
SuperUser = Annotated[Any, Depends(get_superuser)]
