"""
FastStack Admin Module

Provides automatic admin panel with CRUD operations for registered models.
"""

from faststack.admin.registry import admin_registry, register_model
from faststack.admin.routes import router

__all__ = [
    "admin_registry",
    "register_model",
    "router",
]
