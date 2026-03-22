"""
FastStack Authentication Utilities

Provides password hashing, user creation, and authentication helpers.
"""

import secrets
from datetime import datetime
from typing import Any

from passlib.context import CryptContext
from sqlmodel import Session, select

from faststack.auth.models import User, UserCreate
from faststack.config import settings


# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    """
    Hash a plain text password.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_user(
    session: Session,
    email: str,
    password: str,
    is_admin: bool = False,
    **extra_fields: Any,
) -> User:
    """
    Create a new user with hashed password.

    Args:
        session: Database session
        email: User email
        password: Plain text password
        is_admin: Whether user is admin
        **extra_fields: Additional user fields

    Returns:
        Created User instance
    """
    password_hash = hash_password(password)

    user = User(
        email=email,
        password_hash=password_hash,
        is_admin=is_admin,
        **extra_fields,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


def authenticate_user(
    session: Session,
    email: str,
    password: str,
) -> User | None:
    """
    Authenticate a user by email and password.

    Args:
        session: Database session
        email: User email
        password: Plain text password

    Returns:
        User if authenticated, None otherwise
    """
    user = session.exec(select(User).where(User.email == email)).first()

    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    # Update last login
    user.last_login = datetime.utcnow()
    session.add(user)
    session.commit()

    return user


def get_user_by_email(session: Session, email: str) -> User | None:
    """
    Get a user by email address.

    Args:
        session: Database session
        email: User email

    Returns:
        User if found, None otherwise
    """
    return session.exec(select(User).where(User.email == email)).first()


def get_user_by_id(session: Session, user_id: int) -> User | None:
    """
    Get a user by ID.

    Args:
        session: Database session
        user_id: User ID

    Returns:
        User if found, None otherwise
    """
    return session.get(User, user_id)


def generate_password_reset_token() -> str:
    """
    Generate a secure password reset token.

    Returns:
        URL-safe token string
    """
    return secrets.token_urlsafe(32)


def change_password(
    session: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> bool:
    """
    Change a user's password.

    Args:
        session: Database session
        user: User instance
        current_password: Current password for verification
        new_password: New password to set

    Returns:
        True if password changed successfully, False otherwise
    """
    if not verify_password(current_password, user.password_hash):
        return False

    user.password_hash = hash_password(new_password)
    session.add(user)
    session.commit()

    return True


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength based on settings.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, list of errors)
    """
    errors = []

    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(
            f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
        )

    if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if settings.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if settings.PASSWORD_REQUIRE_DIGITS and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")

    if (
        settings.PASSWORD_REQUIRE_SPECIAL
        and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    ):
        errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors
