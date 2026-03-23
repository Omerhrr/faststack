"""
Tests for FastStack Core Functionality

Tests app creation, settings, database, and router functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
import os


class TestSettings:
    """Tests for configuration settings."""

    def test_settings_defaults(self):
        """Test that settings have sensible defaults."""
        from faststack.config import Settings
        
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            
            assert settings.APP_NAME == "FastStack App"
            assert settings.APP_ENV == "development"
            assert settings.DATABASE_URL == "sqlite:///./faststack.db"
            assert settings.PORT == 8000
            assert settings.HOST == "127.0.0.1"

    def test_settings_from_env(self):
        """Test that settings can be loaded from environment variables."""
        from faststack.config import Settings
        
        env_vars = {
            "APP_NAME": "My Test App",
            "APP_ENV": "testing",
            "DATABASE_URL": "postgresql://localhost/test",
            "PORT": "3000",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.APP_NAME == "My Test App"
            assert settings.APP_ENV == "testing"
            assert settings.DATABASE_URL == "postgresql://localhost/test"
            assert settings.PORT == 3000

    def test_is_development_property(self):
        """Test is_development property."""
        from faststack.config import Settings
        
        settings = Settings(APP_ENV="development")
        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.is_testing is False

    def test_is_production_property(self):
        """Test is_production property."""
        from faststack.config import Settings
        
        settings = Settings(APP_ENV="production")
        assert settings.is_production is True
        assert settings.is_development is False
        assert settings.is_testing is False

    def test_is_testing_property(self):
        """Test is_testing property."""
        from faststack.config import Settings
        
        settings = Settings(APP_ENV="testing")
        assert settings.is_testing is True
        assert settings.is_development is False
        assert settings.is_production is False

    def test_secret_key_generation_in_dev(self):
        """Test that SECRET_KEY is auto-generated in development."""
        from faststack.config import Settings
        
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            settings = Settings(APP_ENV="development")
            
            # Should generate a key
            assert settings.SECRET_KEY != ""
            assert len(settings.SECRET_KEY) >= 32

    def test_secret_key_required_in_production(self):
        """Test that SECRET_KEY is required in production."""
        from faststack.config import Settings
        
        with pytest.raises(ValueError, match="SECRET_KEY must be set in production"):
            Settings(APP_ENV="production", SECRET_KEY="")

    def test_cors_origins_parsing(self):
        """Test CORS origins parsing from string."""
        from faststack.config import Settings
        
        settings = Settings(CORS_ORIGINS="http://localhost:3000,http://localhost:8000")
        
        assert "http://localhost:3000" in settings.CORS_ORIGINS
        assert "http://localhost:8000" in settings.CORS_ORIGINS

    def test_cors_credentials_with_wildcard_raises_error(self):
        """Test that CORS credentials with wildcard origins raises error."""
        from faststack.config import Settings
        
        with pytest.raises(ValueError, match="cannot be used with CORS_ORIGINS"):
            Settings(
                CORS_ALLOW_CREDENTIALS=True,
                CORS_ORIGINS=["*"]
            )


class TestAppCreation:
    """Tests for FastAPI app creation."""

    def test_create_app_basic(self, test_app):
        """Test basic app creation."""
        assert test_app is not None
        assert test_app.title == "Test App"
        assert test_app.version == "0.0.1"

    def test_app_has_health_endpoint(self, test_app):
        """Test that app has health check endpoint."""
        routes = [route.path for route in test_app.routes]
        assert "/health" in routes

    def test_app_has_home_endpoint(self, test_app):
        """Test that app has home endpoint."""
        routes = [route.path for route in test_app.routes]
        assert "/" in routes

    def test_create_app_with_custom_settings(self):
        """Test creating app with custom settings."""
        from faststack.app import create_app
        
        app = create_app(
            title="Custom App",
            description="Custom Description",
            version="1.0.0",
            enable_session=False,
            enable_csrf=False,
        )
        
        assert app.title == "Custom App"
        assert app.description == "Custom Description"
        assert app.version == "1.0.0"

    def test_get_app_singleton(self):
        """Test that get_app returns singleton."""
        from faststack.app import get_app, _app
        import faststack.app as app_module
        
        # Reset singleton
        app_module._app = None
        
        app1 = get_app()
        app2 = get_app()
        
        assert app1 is app2


class TestDatabase:
    """Tests for database functionality."""

    def test_get_engine(self):
        """Test getting sync database engine."""
        from faststack.database import get_engine
        
        engine = get_engine()
        assert engine is not None
        assert engine.dialect.name == "sqlite"

    def test_get_async_engine(self):
        """Test getting async database engine."""
        from faststack.database import get_async_engine
        
        engine = get_async_engine()
        assert engine is not None

    def test_get_session(self, db_session):
        """Test getting database session."""
        assert db_session is not None

    def test_init_db(self, db_session):
        """Test initializing database."""
        from faststack.database import init_db, get_engine
        from faststack.auth.models import User
        
        # This should not raise
        init_db()
        
        # Verify tables exist by trying to query
        users = db_session.exec(User).all()
        assert users == []

    def test_session_context_manager(self):
        """Test session as context manager."""
        from faststack.database import session_scope
        
        with session_scope() as session:
            assert session is not None


class TestRouter:
    """Tests for router functionality."""

    def test_router_manager_creation(self):
        """Test RouterManager creation."""
        from faststack.router import RouterManager
        
        rm = RouterManager()
        
        assert rm.api_router is not None
        assert rm.web_router is not None
        assert rm.admin_router is not None
        assert rm.api_router.prefix == "/api"
        assert rm.admin_router.prefix == "/admin"

    def test_register_app(self):
        """Test registering an app with RouterManager."""
        from faststack.router import RouterManager
        from fastapi import APIRouter
        
        rm = RouterManager()
        
        web_router = APIRouter()
        api_router = APIRouter()
        admin_router = APIRouter()
        
        rm.register_app(
            app_name="blog",
            router=web_router,
            api_router=api_router,
            admin_router=admin_router,
        )
        
        assert "blog" in rm._registered_apps
        assert rm._registered_apps["blog"]["router"] is web_router

    def test_api_route_decorator(self):
        """Test api_route decorator."""
        from faststack.router import api_route, router_manager
        
        @api_route("/test", methods=["GET"])
        async def test_endpoint():
            return {"status": "ok"}
        
        # Check that route was added
        routes = [r.path for r in router_manager.api_router.routes]
        assert "/test" in routes

    def test_web_route_decorator(self):
        """Test web_route decorator."""
        from faststack.router import web_route, router_manager
        
        @web_route("/web-test", methods=["GET"])
        async def web_test_endpoint():
            return {"status": "ok"}
        
        # Check that route was added
        routes = [r.path for r in router_manager.web_router.routes]
        assert "/web-test" in routes

    def test_admin_route_decorator(self):
        """Test admin_route decorator."""
        from faststack.router import admin_route, router_manager
        
        @admin_route("/admin-test", methods=["GET"])
        async def admin_test_endpoint():
            return {"status": "ok"}
        
        # Check that route was added
        routes = [r.path for r in router_manager.admin_router.routes]
        assert "/admin-test" in routes
