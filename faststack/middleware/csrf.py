"""
FastStack CSRF Protection

Provides CSRF token generation and validation for forms.
Implements double-submit cookie pattern with session binding.
"""

import hashlib
import hmac
import secrets
import time
import json
from typing import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from faststack.config import settings


class CSRFMiddleware:
    """
    CSRF protection middleware.
    
    Validates CSRF tokens on unsafe HTTP methods (POST, PUT, DELETE, PATCH).
    Tokens can be provided via:
    - X-CSRF-Token header
    - csrf_token form field (including multipart forms)
    - X-XSRF-Token header (for compatibility)
    
    Security features:
    - Tokens are bound to session (if session binding enabled)
    - Tokens have expiration time
    - Origin/Referer validation for additional security
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
    
    # Path prefixes to exclude
    EXEMPT_PREFIXES = [
        "/api/",  # API routes typically use token auth
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
        bind_to_session: bool = True,
        require_origin: bool = False,
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
            bind_to_session: Bind token to session ID
            require_origin: Require Origin/Referer header
        """
        self.app = app
        self.secret_key = secret_key or settings.SECRET_KEY
        self.token_name = token_name
        self.header_name = header_name
        self.cookie_name = cookie_name
        self.expiry = expiry
        self.exempt_paths = exempt_paths or set()
        self.exempt_prefixes = exempt_prefixes or []
        self.bind_to_session = bind_to_session
        self.require_origin = require_origin
    
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
        
        # Generate and set CSRF cookie if not present
        csrf_cookie = request.cookies.get(self.cookie_name)
        
        # Only check CSRF for unsafe methods
        if method in self.UNSAFE_METHODS:
            # Get token from various sources
            token = await self._get_token(request)
            
            if not token:
                response = JSONResponse(
                    {"detail": "CSRF token missing"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )
                await response(scope, receive, send)
                return
            
            # Validate token
            is_valid, error = self._validate_token(request, token, csrf_cookie)
            if not is_valid:
                response = JSONResponse(
                    {"detail": f"CSRF token invalid: {error}"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )
                await response(scope, receive, send)
                return
            
            # Validate origin if required
            if self.require_origin:
                if not self._validate_origin(request):
                    response = JSONResponse(
                        {"detail": "Invalid origin"},
                        status_code=status.HTTP_403_FORBIDDEN,
                    )
                    await response(scope, receive, send)
                    return
        
        # Continue processing
        await self.app(scope, receive, send)
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from CSRF protection."""
        if path in self.EXEMPT_PATHS or path in self.exempt_paths:
            return True
        
        for prefix in self.EXEMPT_PREFIXES + self.exempt_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    async def _get_token(self, request: Request) -> str | None:
        """Get CSRF token from request."""
        # Check headers first
        token = request.headers.get(self.header_name)
        if token:
            return token
        
        # Check X-XSRF-Token header (Angular, etc.)
        token = request.headers.get("X-XSRF-Token")
        if token:
            return token
        
        # Check form data (including multipart)
        content_type = request.headers.get("content-type", "")
        
        if "application/x-www-form-urlencoded" in content_type:
            # Parse form data
            form = await request.form()
            return form.get(self.token_name)
        
        elif "multipart/form-data" in content_type:
            # Parse multipart form data
            try:
                form = await request.form()
                return form.get(self.token_name)
            except Exception:
                pass
        
        elif "application/json" in content_type:
            # Try to get from JSON body
            try:
                body = await request.json()
                return body.get(self.token_name)
            except Exception:
                pass
        
        return None
    
    def _validate_token(
        self, 
        request: Request, 
        token: str, 
        csrf_cookie: str | None
    ) -> tuple[bool, str]:
        """
        Validate a CSRF token.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if token has valid format: timestamp:session_id:signature
            parts = token.split(":")
            
            if len(parts) == 2:
                # Old format: timestamp:signature
                timestamp_str, signature = parts
                session_id = ""
            elif len(parts) == 3:
                # New format: timestamp:session_id:signature
                timestamp_str, session_id, signature = parts
            else:
                return False, "Invalid token format"
            
            try:
                timestamp = int(timestamp_str)
            except ValueError:
                return False, "Invalid timestamp"
            
            # Check expiry
            if time.time() - timestamp > self.expiry:
                return False, "Token expired"
            
            # Verify signature
            expected = self._sign(timestamp, session_id)
            if not hmac.compare_digest(signature, expected):
                return False, "Invalid signature"
            
            # If session binding is enabled, verify session matches
            if self.bind_to_session and session_id:
                current_session_id = self._get_session_id(request)
                if current_session_id and session_id != current_session_id:
                    return False, "Session mismatch"
            
            # Double-submit cookie validation
            if csrf_cookie:
                expected_cookie = self._generate_cookie_value(timestamp, session_id)
                if not hmac.compare_digest(csrf_cookie, expected_cookie):
                    return False, "Cookie mismatch"
            
            return True, ""
        
        except Exception as e:
            return False, str(e)
    
    def _get_session_id(self, request: Request) -> str:
        """Get a session identifier for binding."""
        # Try to get session ID from session middleware
        session = getattr(request, "session", {})
        if session:
            # Use a hash of the session as identifier
            session_str = json.dumps(session, sort_keys=True)
            return hashlib.sha256(session_str.encode()).hexdigest()[:16]
        
        # Fall back to session cookie
        session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if session_cookie:
            return hashlib.sha256(session_cookie.encode()).hexdigest()[:16]
        
        return ""
    
    def _sign(self, timestamp: int, session_id: str = "") -> str:
        """Create a signature for timestamp and session."""
        message = f"{timestamp}:{session_id}".encode()
        return hmac.new(
            self.secret_key.encode(),
            message,
            hashlib.sha256,
        ).hexdigest()
    
    def _generate_cookie_value(self, timestamp: int, session_id: str = "") -> str:
        """Generate a value for the CSRF cookie."""
        return self._sign(timestamp, session_id)
    
    def _validate_origin(self, request: Request) -> bool:
        """Validate Origin or Referer header."""
        origin = request.headers.get("Origin") or request.headers.get("Referer")
        
        if not origin:
            return False
        
        # Parse the origin
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        request_host = request.headers.get("Host", "")
        
        # Check if origin matches request host
        return parsed.netloc == request_host


def generate_csrf_token(
    secret_key: str | None = None,
    session_id: str = "",
    expiry: int = 3600,
) -> str:
    """
    Generate a new CSRF token.
    
    Args:
        secret_key: Secret key for signing (default: from settings)
        session_id: Session identifier for binding
        expiry: Token expiry in seconds (used for validation, not generation)
    
    Returns:
        CSRF token string (timestamp:session_id:signature)
    """
    secret_key = secret_key or settings.SECRET_KEY
    timestamp = int(time.time())
    
    signature = hmac.new(
        secret_key.encode(),
        f"{timestamp}:{session_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    
    if session_id:
        return f"{timestamp}:{session_id}:{signature}"
    return f"{timestamp}:{signature}"


def validate_csrf_token(
    token: str,
    secret_key: str | None = None,
    expiry: int = 3600,
    session_id: str = "",
) -> bool:
    """
    Validate a CSRF token.
    
    Args:
        token: CSRF token to validate
        secret_key: Secret key for verification
        expiry: Maximum token age in seconds
        session_id: Expected session ID (for binding)
    
    Returns:
        True if token is valid
    """
    secret_key = secret_key or settings.SECRET_KEY
    
    try:
        parts = token.split(":")
        
        if len(parts) == 2:
            timestamp_str, signature = parts
            token_session_id = ""
        elif len(parts) == 3:
            timestamp_str, token_session_id, signature = parts
        else:
            return False
        
        timestamp = int(timestamp_str)
        
        if time.time() - timestamp > expiry:
            return False
        
        # Verify session binding if provided
        if session_id and token_session_id and token_session_id != session_id:
            return False
        
        expected = hmac.new(
            secret_key.encode(),
            f"{timestamp}:{token_session_id}".encode(),
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
    session_id = ""
    
    # Get session ID for binding
    session = getattr(request, "session", {})
    if session:
        session_str = json.dumps(session, sort_keys=True)
        session_id = hashlib.sha256(session_str.encode()).hexdigest()[:16]
    
    return generate_csrf_token(session_id=session_id)


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
        # Try form data
        content_type = request.headers.get("content-type", "")
        if "form" in content_type or "multipart" in content_type:
            form = await request.form()
            token = form.get("csrf_token")
    
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


def csrf_input(request: Request) -> str:
    """
    Generate a hidden form input with CSRF token.
    
    Args:
        request: FastAPI request object
    
    Returns:
        HTML string for hidden input
    """
    token = csrf_token(request)
    return f'<input type="hidden" name="csrf_token" value="{token}">'
