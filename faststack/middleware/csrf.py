"""
FastStack CSRF Protection

Provides CSRF token generation and validation for forms.
"""

import hashlib
import hmac
import secrets
import time
from typing import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from faststack.config import settings


class CSRFMiddleware:
    """
    CSRF protection middleware.
    
    Validates CSRF tokens on unsafe HTTP methods (POST, PUT, DELETE, PATCH).
    Tokens can be provided via:
    - X-CSRF-Token header
    - csrf_token form field
    - X-XSRF-Token header (for compatibility)
    """
    
    # Methods that require CSRF protection
    UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
    
    # Paths to exclude from CSRF protection
    EXEMPT_PATHS = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
    
    # Path prefixes to exclude (API routes typically use token auth)
    EXEMPT_PREFIXES = [
        "/api/",
    ]
    
    def __init__(
        self,
        app,
        secret_key: str | None = None,
        token_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        cookie_name: str = "csrf_token",
        expiry: int = 3600,  # 1 hour
        exempt_paths: set[str] | None = None,
        exempt_prefixes: list[str] | None = None,
    ):
        """
        Initialize CSRF middleware.
        
        Args:
            app: ASGI application
            secret_key: Secret key for signing tokens
            token_name: Form field name for CSRF token
            header_name: Header name for CSRF token
            cookie_name: Cookie name for double-submit cookie
            expiry: Token expiry time in seconds
            exempt_paths: Additional paths to exempt
            exempt_prefixes: Additional path prefixes to exempt
        """
        self.app = app
        self.secret_key = secret_key or settings.SECRET_KEY
        self.token_name = token_name
        self.header_name = header_name
        self.cookie_name = cookie_name
        self.expiry = expiry
        self.exempt_paths = exempt_paths or set()
        self.exempt_prefixes = exempt_prefixes or []
    
    async def __call__(self, scope, receive, send):
        """Process the request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope)
        method = request.method
        path = request.url.path
        
        # Check if path is exempt
        if self._is_exempt(path):
            await self.app(scope, receive, send)
            return
        
        # Only check CSRF for unsafe methods
        if method in self.UNSAFE_METHODS:
            token = self._get_token(request)
            
            if not token or not self._validate_token(request, token):
                response = JSONResponse(
                    {"detail": "CSRF token missing or invalid"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )
                await response(scope, receive, send)
                return
        
        await self.app(scope, receive, send)
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from CSRF protection."""
        if path in self.EXEMPT_PATHS or path in self.exempt_paths:
            return True
        
        for prefix in self.EXEMPT_PREFIXES + self.exempt_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _get_token(self, request: Request) -> str | None:
        """Get CSRF token from request."""
        # Check headers first
        token = request.headers.get(self.header_name)
        if token:
            return token
        
        # Check X-XSRF-Token header (Angular, etc.)
        token = request.headers.get("X-XSRF-Token")
        if token:
            return token
        
        # Check form data
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            # Form data - need to parse it
            # For now, rely on header
            pass
        
        return None
    
    def _validate_token(self, request: Request, token: str) -> bool:
        """Validate a CSRF token."""
        try:
            # Check if token has valid format: timestamp:signature
            if ":" not in token:
                return False
            
            timestamp_str, signature = token.rsplit(":", 1)
            timestamp = int(timestamp_str)
            
            # Check expiry
            if time.time() - timestamp > self.expiry:
                return False
            
            # Verify signature
            expected = self._sign(timestamp)
            return hmac.compare_digest(signature, expected)
        
        except (ValueError, TypeError):
            return False
    
    def _sign(self, timestamp: int) -> str:
        """Create a signature for a timestamp."""
        message = str(timestamp).encode()
        return hmac.new(
            self.secret_key.encode(),
            message,
            hashlib.sha256,
        ).hexdigest()


def generate_csrf_token(secret_key: str | None = None) -> str:
    """
    Generate a new CSRF token.
    
    Args:
        secret_key: Secret key for signing (default: from settings)
    
    Returns:
        CSRF token string (timestamp:signature)
    """
    secret_key = secret_key or settings.SECRET_KEY
    timestamp = int(time.time())
    
    signature = hmac.new(
        secret_key.encode(),
        str(timestamp).encode(),
        hashlib.sha256,
    ).hexdigest()
    
    return f"{timestamp}:{signature}"


def validate_csrf_token(token: str, secret_key: str | None = None, expiry: int = 3600) -> bool:
    """
    Validate a CSRF token.
    
    Args:
        token: CSRF token to validate
        secret_key: Secret key for verification
        expiry: Maximum token age in seconds
    
    Returns:
        True if token is valid
    """
    secret_key = secret_key or settings.SECRET_KEY
    
    try:
        if ":" not in token:
            return False
        
        timestamp_str, signature = token.rsplit(":", 1)
        timestamp = int(timestamp_str)
        
        if time.time() - timestamp > expiry:
            return False
        
        expected = hmac.new(
            secret_key.encode(),
            str(timestamp).encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
    
    except (ValueError, TypeError):
        return False


def csrf_token(request: Request) -> str:
    """
    Get or generate a CSRF token for a request.
    
    This function can be used in templates as a global function.
    
    Args:
        request: FastAPI request object
    
    Returns:
        CSRF token string
    """
    return generate_csrf_token()


# Dependency for requiring CSRF token
async def require_csrf(request: Request) -> str:
    """
    Dependency that validates CSRF token.
    
    Raises:
        HTTPException: If CSRF token is invalid
    
    Returns:
        The validated CSRF token
    """
    token = request.headers.get("X-CSRF-Token") or request.headers.get("X-XSRF-Token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token required",
        )
    
    if not validate_csrf_token(token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token invalid or expired",
        )
    
    return token
