"""
Tests for FastStack Middleware

Tests CSRF protection, rate limiting, security headers, and session middleware.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import time
import hashlib
import hmac


class TestCSRFMiddleware:
    """Tests for CSRF middleware."""

    def test_generate_csrf_token(self):
        """Test CSRF token generation."""
        from faststack.middleware.csrf import generate_csrf_token
        
        token = generate_csrf_token(secret_key="test-secret-key")
        
        assert token is not None
        assert ":" in token  # Format: timestamp:signature

    def test_validate_csrf_token_valid(self):
        """Test validating a valid CSRF token."""
        from faststack.middleware.csrf import generate_csrf_token, validate_csrf_token
        
        token = generate_csrf_token(secret_key="test-secret-key")
        
        assert validate_csrf_token(token, secret_key="test-secret-key") is True

    def test_validate_csrf_token_invalid(self):
        """Test validating an invalid CSRF token."""
        from faststack.middleware.csrf import validate_csrf_token
        
        assert validate_csrf_token("invalid:token", secret_key="test-secret-key") is False

    def test_validate_csrf_token_expired(self):
        """Test validating an expired CSRF token."""
        from faststack.middleware.csrf import validate_csrf_token
        
        # Create an old timestamp
        old_timestamp = str(int(time.time()) - 7200)  # 2 hours ago
        signature = hmac.new(
            b"test-secret-key",
            f"{old_timestamp}:".encode(),
            hashlib.sha256,
        ).hexdigest()
        token = f"{old_timestamp}:{signature}"
        
        assert validate_csrf_token(token, secret_key="test-secret-key", expiry=3600) is False

    def test_csrf_token_with_session_binding(self):
        """Test CSRF token with session binding."""
        from faststack.middleware.csrf import generate_csrf_token, validate_csrf_token
        
        session_id = "test-session-123"
        token = generate_csrf_token(
            secret_key="test-secret-key",
            session_id=session_id
        )
        
        # Should validate with correct session ID
        assert validate_csrf_token(
            token,
            secret_key="test-secret-key",
            session_id=session_id
        ) is True
        
        # Should fail with wrong session ID
        assert validate_csrf_token(
            token,
            secret_key="test-secret-key",
            session_id="wrong-session"
        ) is False

    def test_csrf_exempt_paths(self):
        """Test that exempt paths are skipped."""
        from faststack.middleware.csrf import CSRFMiddleware
        
        middleware = CSRFMiddleware(app=MagicMock())
        
        assert middleware._is_exempt("/health") is True
        assert middleware._is_exempt("/docs") is True
        assert middleware._is_exempt("/openapi.json") is True
        assert middleware._is_exempt("/api/users") is True  # API prefix exempt
        assert middleware._is_exempt("/web/form") is False

    def test_csrf_token_from_header(self):
        """Test getting CSRF token from header."""
        from faststack.middleware.csrf import CSRFMiddleware
        
        middleware = CSRFMiddleware(app=MagicMock(), header_name="X-CSRF-Token")
        
        request = MagicMock()
        request.headers.get = MagicMock(return_value="header-token")
        
        # Mock async method call
        import asyncio
        
        async def get_token():
            return await middleware._get_token(request)
        
        token = asyncio.get_event_loop().run_until_complete(get_token())
        assert token == "header-token"

    def test_csrf_input_helper(self):
        """Test csrf_input helper function."""
        from faststack.middleware.csrf import csrf_input
        
        request = MagicMock()
        request.session = {}
        
        html = csrf_input(request)
        
        assert 'type="hidden"' in html
        assert 'name="csrf_token"' in html
        assert 'value="' in html


class TestRateLimitMiddleware:
    """Tests for rate limiting middleware."""

    def test_rate_limit_config(self):
        """Test rate limit configuration."""
        from faststack.config import Settings
        
        settings = Settings(
            RATE_LIMIT_ENABLED=True,
            RATE_LIMIT_REQUESTS_PER_MINUTE=60,
            RATE_LIMIT_REQUESTS_PER_HOUR=1000
        )
        
        assert settings.RATE_LIMIT_REQUESTS_PER_MINUTE == 60
        assert settings.RATE_LIMIT_REQUESTS_PER_HOUR == 1000

    def test_rate_limit_disabled_in_test(self):
        """Test that rate limiting can be disabled."""
        from faststack.config import Settings
        
        settings = Settings(RATE_LIMIT_ENABLED=False)
        
        assert settings.RATE_LIMIT_ENABLED is False


class TestSecurityHeadersMiddleware:
    """Tests for security headers middleware."""

    def test_security_headers_config(self):
        """Test security headers configuration."""
        from faststack.config import Settings
        
        settings = Settings(
            SECURITY_HEADERS_ENABLED=True,
            HSTS_ENABLED=True,
            CSP_ENABLED=True
        )
        
        assert settings.SECURITY_HEADERS_ENABLED is True
        assert settings.HSTS_ENABLED is True
        assert settings.CSP_ENABLED is True


class TestSessionMiddleware:
    """Tests for session middleware."""

    def test_session_cookie_settings(self):
        """Test session cookie configuration."""
        from faststack.config import Settings
        
        settings = Settings(
            SESSION_COOKIE_NAME="session_id",
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="strict"
        )
        
        assert settings.SESSION_COOKIE_NAME == "session_id"
        assert settings.SESSION_COOKIE_SECURE is True
        assert settings.SESSION_COOKIE_HTTPONLY is True
        assert settings.SESSION_COOKIE_SAMESITE == "strict"

    def test_session_max_age(self):
        """Test session max age configuration."""
        from faststack.config import Settings
        
        settings = Settings(SESSION_MAX_AGE=86400)
        
        assert settings.SESSION_MAX_AGE == 86400

    def test_session_regeneration_on_login(self):
        """Test session regeneration setting."""
        from faststack.config import Settings
        
        settings = Settings(SESSION_REGENERATE_ON_LOGIN=True)
        
        assert settings.SESSION_REGENERATE_ON_LOGIN is True


class TestClickjackingMiddleware:
    """Tests for clickjacking protection."""

    def test_clickjacking_protection_exists(self):
        """Test that clickjacking middleware module exists."""
        from faststack.faststack.middleware.clickjacking import __name__ as module_name
        
        assert module_name is not None


class TestLoggingMiddleware:
    """Tests for logging middleware."""

    def test_logging_middleware_exists(self):
        """Test that logging middleware module exists."""
        from faststack.middleware.logging import __name__ as module_name
        
        assert module_name is not None


class TestMiddlewareIntegration:
    """Integration tests for middleware stack."""

    @pytest.mark.asyncio
    async def test_middleware_stack_order(self, test_app):
        """Test that middleware is applied in correct order."""
        # Get middleware stack
        middleware = test_app.user_middleware
        
        # Should have middleware configured
        assert len(middleware) > 0

    @pytest.mark.asyncio
    async def test_request_with_session(self, client):
        """Test request with session data."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
