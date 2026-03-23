"""
Tests for FastStack Views

Tests generic views, view mixins, and HTMX responses.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestHTMXResponse:
    """Tests for HTMX response utilities."""

    def test_htmx_redirect(self):
        """Test HTMX redirect response."""
        from faststack.core.responses import HTMXResponse
        
        response = HTMXResponse.redirect("/dashboard")
        
        assert response.status_code == 200
        assert response.headers.get("HX-Redirect") == "/dashboard"

    def test_htmx_trigger(self):
        """Test HTMX trigger response."""
        from faststack.core.responses import HTMXResponse
        
        response = HTMXResponse.trigger(
            content="<div>Done</div>",
            event="itemAdded",
            params={"id": 1}
        )
        
        assert response.status_code == 200
        assert "HX-Trigger" in response.headers

    def test_htmx_refresh(self):
        """Test HTMX refresh response."""
        from faststack.core.responses import HTMXResponse
        
        response = HTMXResponse.refresh()
        
        assert response.status_code == 200
        assert response.headers.get("HX-Refresh") == "true"

    def test_htmx_retarget(self):
        """Test HTMX retarget response."""
        from faststack.core.responses import HTMXResponse
        
        response = HTMXResponse.retarget(
            content="<div>New content</div>",
            target="#modal"
        )
        
        assert response.status_code == 200
        assert response.headers.get("HX-Retarget") == "#modal"

    def test_htmx_push_url(self):
        """Test HTMX push URL response."""
        from faststack.core.responses import HTMXResponse
        
        response = HTMXResponse.push_url(
            content="<div>Content</div>",
            url="/new-page"
        )
        
        assert response.status_code == 200
        assert response.headers.get("HX-Push-Url") == "/new-page"

    def test_htmx_swap(self):
        """Test HTMX swap response."""
        from faststack.core.responses import HTMXResponse
        
        response = HTMXResponse.swap(
            content="<div>Content</div>",
            swap="outerHTML"
        )
        
        assert response.status_code == 200
        assert response.headers.get("HX-Reswap") == "outerHTML"


class TestHTMXDetection:
    """Tests for HTMX request detection."""

    def test_is_htmx_true(self):
        """Test detecting HTMX request."""
        from faststack.core.responses import is_htmx
        
        request = MagicMock()
        request.headers.get = MagicMock(return_value="true")
        
        assert is_htmx(request) is True

    def test_is_htmx_false(self):
        """Test detecting non-HTMX request."""
        from faststack.core.responses import is_htmx
        
        request = MagicMock()
        request.headers.get = MagicMock(return_value="false")
        
        assert is_htmx(request) is False

    def test_get_htmx_target(self):
        """Test getting HTMX target."""
        from faststack.core.responses import get_htmx_target
        
        request = MagicMock()
        request.headers.get = MagicMock(return_value="#content")
        
        assert get_htmx_target(request) == "#content"

    def test_get_htmx_trigger(self):
        """Test getting HTMX trigger."""
        from faststack.core.responses import get_htmx_trigger
        
        request = MagicMock()
        request.headers.get = MagicMock(return_value="submit-btn")
        
        assert get_htmx_trigger(request) == "submit-btn"

    def test_get_htmx_prompt(self):
        """Test getting HTMX prompt response."""
        from faststack.core.responses import get_htmx_prompt
        
        request = MagicMock()
        request.headers.get = MagicMock(return_value="user input")
        
        assert get_htmx_prompt(request) == "user input"


class TestGenericViews:
    """Tests for generic views."""

    def test_view_base_exists(self):
        """Test that View base class exists."""
        from faststack.faststack.views.base import View
        
        assert View is not None

    def test_template_view_exists(self):
        """Test that TemplateView exists."""
        from faststack.faststack.views.generic import TemplateView
        
        assert TemplateView is not None

    def test_list_view_exists(self):
        """Test that ListView exists."""
        from faststack.faststack.views.generic import ListView
        
        assert ListView is not None

    def test_detail_view_exists(self):
        """Test that DetailView exists."""
        from faststack.faststack.views.generic import DetailView
        
        assert DetailView is not None

    def test_create_view_exists(self):
        """Test that CreateView exists."""
        from faststack.faststack.views.generic import CreateView
        
        assert CreateView is not None

    def test_update_view_exists(self):
        """Test that UpdateView exists."""
        from faststack.faststack.views.generic import UpdateView
        
        assert UpdateView is not None

    def test_delete_view_exists(self):
        """Test that DeleteView exists."""
        from faststack.faststack.views.generic import DeleteView
        
        assert DeleteView is not None


class TestViewMixins:
    """Tests for view mixins."""

    def test_login_required_mixin_exists(self):
        """Test that LoginRequiredMixin exists."""
        from faststack.faststack.views.mixins import LoginRequiredMixin
        
        assert LoginRequiredMixin is not None

    def test_permission_required_mixin_exists(self):
        """Test that PermissionRequiredMixin exists."""
        from faststack.faststack.views.mixins import PermissionRequiredMixin
        
        assert PermissionRequiredMixin is not None

    def test_paginate_mixin_exists(self):
        """Test that PaginateMixin exists."""
        from faststack.faststack.views.mixins import PaginateMixin
        
        assert PaginateMixin is not None


class TestPagination:
    """Tests for pagination functionality."""

    def test_paginator_creation(self):
        """Test creating a paginator."""
        from faststack.core.pagination.paginator import Paginator
        
        items = list(range(100))
        paginator = Paginator(items, per_page=10)
        
        assert paginator.total_items == 100
        assert paginator.per_page == 10
        assert paginator.total_pages == 10

    def test_paginator_get_page(self):
        """Test getting a page from paginator."""
        from faststack.core.pagination.paginator import Paginator
        
        items = list(range(100))
        paginator = Paginator(items, per_page=10)
        
        page = paginator.get_page(1)
        
        assert len(page.items) == 10
        assert page.items == list(range(0, 10))

    def test_paginator_invalid_page(self):
        """Test paginator with invalid page number."""
        from faststack.core.pagination.paginator import Paginator
        
        items = list(range(100))
        paginator = Paginator(items, per_page=10)
        
        # Page 0 should return first page
        page = paginator.get_page(0)
        assert page.number == 1
        
        # Page beyond total should return last page
        page = paginator.get_page(100)
        assert page.number == 10

    def test_page_properties(self):
        """Test page object properties."""
        from faststack.core.pagination.paginator import Paginator
        
        items = list(range(100))
        paginator = Paginator(items, per_page=10)
        page = paginator.get_page(5)
        
        assert page.has_previous() is True
        assert page.has_next() is True
        assert page.previous_page_number() == 4
        assert page.next_page_number() == 6


class TestRedirects:
    """Tests for redirect functionality."""

    def test_redirect_response(self):
        """Test creating redirect response."""
        from faststack.core.responses import redirect
        
        response = redirect("/login", status_code=302)
        
        assert response.status_code == 302
        assert response.headers.get("location") == "/login"

    def test_permanent_redirect(self):
        """Test permanent redirect."""
        from faststack.core.responses import redirect
        
        response = redirect("/new-location", status_code=301)
        
        assert response.status_code == 301


class TestViewIntegration:
    """Integration tests for views with app."""

    @pytest.mark.asyncio
    async def test_home_page(self, client):
        """Test home page renders."""
        response = await client.get("/")
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_404_error(self, client):
        """Test 404 error page."""
        response = await client.get("/nonexistent-page-12345")
        
        assert response.status_code == 404
