"""
FastStack Request Logging Middleware

Logs all HTTP requests with timing and status information.
"""

import logging
import time
import json
from typing import Any
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Configure logger
logger = logging.getLogger("faststack.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all HTTP requests.
    
    Logs include:
    - Request method and path
    - Response status code
    - Request duration
    - Client IP address
    - User agent
    """
    
    def __init__(
        self,
        app,
        logger: logging.Logger | None = None,
        log_level: int = logging.INFO,
        log_body: bool = False,
        exclude_paths: list[str] | None = None,
        sensitive_headers: list[str] | None = None,
    ):
        """
        Initialize request logging middleware.
        
        Args:
            app: ASGI application
            logger: Logger to use (default: faststack.requests)
            log_level: Log level for requests
            log_body: If True, log request/response bodies
            exclude_paths: Paths to exclude from logging
            sensitive_headers: Header names to mask in logs
        """
        super().__init__(app)
        self.logger = logger or logging.getLogger("faststack.requests")
        self.log_level = log_level
        self.log_body = log_body
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
        self.sensitive_headers = sensitive_headers or [
            "authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
            "x-auth-token",
        ]
    
    def _mask_sensitive(self, headers: dict) -> dict:
        """Mask sensitive headers."""
        masked = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                masked[key] = "***MASKED***"
            else:
                masked[key] = value
        return masked
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and log details."""
        # Check if path should be excluded
        path = request.url.path
        if any(path.startswith(exclude) for exclude in self.exclude_paths):
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Log request
        request_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": path,
            "query": str(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", ""),
        }
        
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if len(body) < 1000:  # Don't log large bodies
                    request_data["body_length"] = len(body)
            except Exception:
                pass
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        log_data = {
            **request_data,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        }
        
        # Log based on status code
        if response.status_code >= 500:
            self.logger.error(json.dumps(log_data))
        elif response.status_code >= 400:
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.log(self.log_level, json.dumps(log_data))
        
        return response
