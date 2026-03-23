"""
Tests for FastStack Admin

Tests admin registration, dashboard, and CRUD operations.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestAdminRegistry:
    """Tests for admin registry."""

    def test_registry_exists(self):
        """Test that admin registry exists."""
        from faststack.admin.registry import admin_registry
        
        assert admin_registry is not None

    def test_register_model(self):
        """Test registering a model with admin."""
        from faststack.admin.registry import admin_registry
        from faststack.orm.base import BaseModel
        
        class TestModel(BaseModel, table=True):
            __tablename__ = "test_model_admin"
            name: str = "test"
        
        admin_registry.register(TestModel)
        
        # Check model was registered
        registered = admin_registry.get_model("TestModel")
        assert registered is not None

    def test_get_models(self):
        """Test getting registered models."""
        from faststack.admin.registry import admin_registry
        
        models = admin_registry.get_all_models()
        
        assert isinstance(models, dict)


class TestAdminRoutes:
    """Tests for admin routes."""

    def test_admin_routes_exist(self):
        """Test that admin routes module exists."""
        from faststack.admin import routes
        
        assert routes is not None

    def test_admin_router(self):
        """Test admin router."""
        from faststack.admin.routes import router
        
        assert router is not None


class TestAdminViews:
    """Tests for admin views."""

    def test_admin_view_exists(self):
        """Test that admin view exists."""
        from faststack.faststack.contrib.admin.views import AdminSite
        
        assert AdminSite is not None


class TestAdminConfiguration:
    """Tests for admin configuration."""

    def test_admin_settings(self):
        """Test admin settings."""
        from faststack.config import Settings
        
        settings = Settings(
            ADMIN_MOUNT_PATH="/admin",
            ADMIN_SITE_HEADER="Test Admin",
            ADMIN_SITE_TITLE="Test Administration"
        )
        
        assert settings.ADMIN_MOUNT_PATH == "/admin"
        assert settings.ADMIN_SITE_HEADER == "Test Admin"
        assert settings.ADMIN_SITE_TITLE == "Test Administration"

    def test_admin_optimistic_locking(self):
        """Test admin optimistic locking setting."""
        from faststack.config import Settings
        
        settings = Settings(ADMIN_OPTIMISTIC_LOCKING=True)
        
        assert settings.ADMIN_OPTIMISTIC_LOCKING is True


class TestAdminIntegration:
    """Integration tests for admin functionality."""

    @pytest.mark.asyncio
    async def test_admin_requires_auth(self, client):
        """Test that admin requires authentication."""
        response = await client.get("/admin/")
        
        # Should redirect to login or return 401
        assert response.status_code in [302, 401, 403]
