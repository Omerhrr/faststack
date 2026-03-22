"""
FastStack Security Headers Middleware

Adds security-related headers to all responses.
"""

from typing import Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.
    
    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: restrictive defaults
    - Content-Security-Policy: basic CSP
    """
    
    def __init__(
        self,
        app,
        content_type_options: str = "nosniff",
        frame_options: str = "DENY",
        xss_protection: str = "1; mode=block",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: str | None = None,
        content_security_policy: str | None = None,
        strict_transport_security: str | None = None,
        enable_hsts: bool = False,
    ):
        """
        Initialize security headers middleware.
        
        Args:
            app: ASGI application
            content_type_options: X-Content-Type-Options value
            frame_options: X-Frame-Options value
            xss_protection: X-XSS-Protection value
            referrer_policy: Referrer-Policy value
            permissions_policy: Permissions-Policy value
            content_security_policy: Content-Security-Policy value
            strict_transport_security: Strict-Transport-Security value
            enable_hsts: If True, enable HSTS with default settings
        """
        super().__init__(app)
        self.headers = {
            "X-Content-Type-Options": content_type_options,
            "X-Frame-Options": frame_options,
            "X-XSS-Protection": xss_protection,
            "Referrer-Policy": referrer_policy,
        }
        
        if permissions_policy:
            self.headers["Permissions-Policy"] = permissions_policy
        else:
            # Default restrictive permissions policy
            self.headers["Permissions-Policy"] = (
                "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
                "magnetometer=(), microphone=(), payment=(), usb=()"
            )
        
        if content_security_policy:
            self.headers["Content-Security-Policy"] = content_security_policy
        else:
            # Basic CSP - more restrictive than nothing
            self.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://unpkg.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
                "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https:;"
            )
        
        if enable_hsts:
            if strict_transport_security:
                self.headers["Strict-Transport-Security"] = strict_transport_security
            else:
                self.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add security headers."""
        response = await call_next(request)
        
        for header, value in self.headers.items():
            response.headers[header] = value
        
        return response
