"""
FastStack Auto-Admin Interface

A Django-like automatic admin interface for managing models.

Example:
    # In your app
    from faststack.contrib.admin import admin
    from myapp.models import User, Post

    admin.register(User)
    admin.register(Post)

    # Custom admin
    @admin.register(User)
    class UserAdmin(admin.ModelAdmin):
        list_display = ['username', 'email', 'is_active']
        list_filter = ['is_active', 'is_staff']
        search_fields = ['username', 'email']
"""

from .registry import admin, AdminSite, ModelAdmin, register
from .views import AdminView, AdminListView, AdminCreateView, AdminUpdateView, AdminDeleteView

__all__ = [
    'admin',
    'AdminSite',
    'ModelAdmin',
    'register',
    'AdminView',
    'AdminListView',
    'AdminCreateView',
    'AdminUpdateView',
    'AdminDeleteView',
]
