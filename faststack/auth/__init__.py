"""
FastStack Authentication Module

Provides user authentication, password hashing, and session management.
"""

from faststack.auth.models import User
from faststack.auth.utils import (
    hash_password,
    verify_password,
    create_user,
    authenticate_user,
)
from faststack.auth.routes import router

__all__ = [
    "User",
    "hash_password",
    "verify_password",
    "create_user",
    "authenticate_user",
    "router",
]
