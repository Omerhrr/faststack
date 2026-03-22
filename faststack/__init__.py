"""
FastStack - Async-first Python framework built on FastAPI
with integrated templating, ORM, admin, and CLI.

FastStack combines the power of FastAPI with Django-like developer experience,
providing:
- Automatic app discovery and loading
- Integrated SQLModel ORM with migrations
- Built-in authentication and admin panel
- Jinja2 templating with HTMX support
- Modern CLI powered by Typer
"""

__version__ = "0.1.0"
__author__ = "FastStack Team"

from faststack.app import create_app, get_app
from faststack.config import settings
from faststack.database import get_session, init_db, engine
from faststack.orm.base import BaseModel, TimestampMixin

__all__ = [
    "__version__",
    "create_app",
    "get_app",
    "settings",
    "get_session",
    "init_db",
    "engine",
    "BaseModel",
    "TimestampMixin",
]
