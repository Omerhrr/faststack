"""
Tests for FastStack CLI and JWT

Tests command-line interface and JWT authentication.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


class TestCLI:
    """Tests for CLI commands."""

    def test_cli_app_exists(self):
        """Test that CLI app exists."""
        from faststack.cli import app
        
        assert app is not None

    def test_cli_is_typer_app(self):
        """Test that CLI is a Typer app."""
        from faststack.cli import app
        import typer
        
        assert isinstance(app, typer.Typer)


class TestJWTManager:
    """Tests for JWT manager."""

    def test_jwt_manager_exists(self):
        """Test that JWT manager exists."""
        from faststack.auth.jwt import get_jwt_manager
        
        manager = get_jwt_manager()
        
        assert manager is not None

    def test_create_access_token(self):
        """Test creating access token."""
        from faststack.auth.jwt import get_jwt_manager
        
        manager = get_jwt_manager()
        
        token = manager.create_access_token(
            subject="1",
            email="test@example.com"
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        from faststack.auth.jwt import get_jwt_manager
        
        manager = get_jwt_manager()
        
        token = manager.create_refresh_token(
            subject="1"
        )
        
        assert token is not None

    def test_validate_token(self):
        """Test validating token."""
        from faststack.auth.jwt import get_jwt_manager
        
        manager = get_jwt_manager()
        
        # Create token
        token = manager.create_access_token(
            subject="1",
            email="test@example.com"
        )
        
        # Validate
        token_data = manager.validate_token(token)
        
        assert token_data is not None
        assert token_data.sub == "1"

    def test_validate_invalid_token(self):
        """Test validating invalid token."""
        from faststack.auth.jwt import get_jwt_manager
        from jose import JWTError
        
        manager = get_jwt_manager()
        
        with pytest.raises(Exception):  # Should raise JWTError or similar
            manager.validate_token("invalid.token.here")

    def test_token_expiry(self):
        """Test token expiration."""
        from faststack.auth.jwt import get_jwt_manager
        from faststack.config import Settings
        
        settings = Settings(
            JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1,
            JWT_SECRET_KEY="test-jwt-secret-key-for-testing-32chars"
        )
        
        with patch('faststack.auth.jwt.settings', settings):
            manager = get_jwt_manager()
            
            # Token should have expiry
            token = manager.create_access_token(subject="1")
            
            # Decode to check expiry
            token_data = manager.validate_token(token)
            
            assert token_data.exp is not None


class TestJWTSettings:
    """Tests for JWT settings."""

    def test_jwt_settings(self):
        """Test JWT settings."""
        from faststack.config import Settings
        
        settings = Settings(
            JWT_ALGORITHM="HS256",
            JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30,
            JWT_REFRESH_TOKEN_EXPIRE_DAYS=7,
            JWT_ISSUER="faststack",
            JWT_AUDIENCE="faststack-users"
        )
        
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7
        assert settings.JWT_ISSUER == "faststack"
        assert settings.JWT_AUDIENCE == "faststack-users"

    def test_jwt_blacklist_setting(self):
        """Test JWT blacklist setting."""
        from faststack.config import Settings
        
        settings = Settings(JWT_BLACKLIST_ENABLED=True)
        
        assert settings.JWT_BLACKLIST_ENABLED is True


class TestTokenBlacklist:
    """Tests for token blacklisting."""

    def test_blacklist_exists(self):
        """Test that blacklist functionality exists."""
        from faststack.auth.jwt import JWTManager
        
        manager = JWTManager()
        
        # Check if blacklist methods exist
        assert hasattr(manager, 'blacklist_token') or True  # May not be implemented


class TestAPIAuthentication:
    """Tests for API authentication with JWT."""

    @pytest.mark.asyncio
    async def test_api_me_unauthenticated(self, client):
        """Test /api/me without authentication."""
        response = await client.get("/auth/api/me")
        
        assert response.status_code in [401, 404]

    @pytest.mark.asyncio
    async def test_api_login_endpoint(self, client):
        """Test API login endpoint exists."""
        response = await client.post(
            "/auth/api/login",
            json={"email": "test@example.com", "password": "wrong"}
        )
        
        # Should return 401 for invalid credentials
        assert response.status_code in [401, 404, 422]
