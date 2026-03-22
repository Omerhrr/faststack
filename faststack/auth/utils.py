"""
FastStack Authentication Utilities

Provides password hashing, user creation, and authentication helpers.
Includes brute force protection and account lockout.
"""

import secrets
from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict
import asyncio
import time

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


# In-memory store for failed attempts (use Redis in production)
_failed_attempts: dict[str, list[float]] = defaultdict(list)
_lockouts: dict[str, float] = {}
_failed_attempts_lock = asyncio.Lock()


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
    
    Includes brute force protection with account lockout.

    Args:
        session: Database session
        email: User email
        password: Plain text password

    Returns:
        User if authenticated, None otherwise
    """
    # Check if account is locked
    if is_account_locked(email):
        return None
    
    user = session.exec(select(User).where(User.email == email)).first()

    if user is None:
        # Record failed attempt for non-existent user (don't reveal existence)
        record_failed_attempt(email)
        return None

    if not verify_password(password, user.password_hash):
        # Record failed attempt
        record_failed_attempt(email)
        return None
    
    # Clear failed attempts on successful login
    clear_failed_attempts(email)
    
    # Check if account is active
    if not user.is_active:
        return None

    # Update last login
    user.last_login = datetime.utcnow()
    session.add(user)
    session.commit()

    return user


def record_failed_attempt(identifier: str) -> None:
    """
    Record a failed login attempt.
    
    Args:
        identifier: Email or IP address
    """
    if not settings.BRUTE_FORCE_ENABLED:
        return
    
    now = time.time()
    _failed_attempts[identifier].append(now)
    
    # Clean old attempts (older than lockout duration)
    cutoff = now - settings.BRUTE_FORCE_LOCKOUT_DURATION
    _failed_attempts[identifier] = [
        ts for ts in _failed_attempts[identifier] if ts > cutoff
    ]


def get_failed_attempts(identifier: str) -> int:
    """
    Get the number of recent failed attempts.
    
    Args:
        identifier: Email or IP address
    
    Returns:
        Number of failed attempts in the lockout window
    """
    now = time.time()
    cutoff = now - settings.BRUTE_FORCE_LOCKOUT_DURATION
    return len([
        ts for ts in _failed_attempts.get(identifier, [])
        if ts > cutoff
    ])


def is_account_locked(identifier: str) -> bool:
    """
    Check if an account is locked due to too many failed attempts.
    
    Args:
        identifier: Email or IP address
    
    Returns:
        True if account is locked
    """
    if not settings.BRUTE_FORCE_ENABLED:
        return False
    
    # Check explicit lockout
    if identifier in _lockouts:
        if time.time() < _lockouts[identifier]:
            return True
        else:
            del _lockouts[identifier]
    
    # Check failed attempts count
    attempts = get_failed_attempts(identifier)
    return attempts >= settings.BRUTE_FORCE_MAX_ATTEMPTS


def lock_account(identifier: str, duration: int | None = None) -> None:
    """
    Lock an account for a specified duration.
    
    Args:
        identifier: Email or IP address
        duration: Lockout duration in seconds (default: from settings)
    """
    duration = duration or settings.BRUTE_FORCE_LOCKOUT_DURATION
    _lockouts[identifier] = time.time() + duration


def clear_failed_attempts(identifier: str) -> None:
    """
    Clear failed attempts for an identifier.
    
    Args:
        identifier: Email or IP address
    """
    _failed_attempts.pop(identifier, None)
    _lockouts.pop(identifier, None)


def get_lockout_remaining(identifier: str) -> int:
    """
    Get the remaining lockout time in seconds.
    
    Args:
        identifier: Email or IP address
    
    Returns:
        Remaining seconds, or 0 if not locked
    """
    if identifier in _lockouts:
        remaining = _lockouts[identifier] - time.time()
        return max(0, int(remaining))
    return 0


def get_progressive_delay(identifier: str) -> float:
    """
    Get a progressive delay for rate limiting.
    
    Returns increasing delay after each failed attempt.
    
    Args:
        identifier: Email or IP address
    
    Returns:
        Delay in seconds
    """
    if not settings.BRUTE_FORCE_PROGRESSIVE_DELAY:
        return 0
    
    attempts = get_failed_attempts(identifier)
    if attempts == 0:
        return 0
    
    # Exponential backoff: 1s, 2s, 4s, 8s, 16s, ...
    return min(2 ** (attempts - 1), 60)  # Max 60 seconds


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


def check_password_history(
    session: Session,
    user: User,
    new_password: str,
) -> bool:
    """
    Check if new password is in user's password history.
    
    Args:
        session: Database session
        user: User instance
        new_password: New password to check
    
    Returns:
        True if password is NOT in history (allowed), False if it is
    """
    if settings.PASSWORD_HISTORY_COUNT <= 0:
        return True
    
    # Get password history from user's metadata or separate model
    # This is a simplified implementation - in production, store hashes separately
    history = getattr(user, "_password_history", [])
    
    for old_hash in history[-settings.PASSWORD_HISTORY_COUNT:]:
        if verify_password(new_password, old_hash):
            return False
    
    return True


def generate_api_token() -> str:
    """
    Generate a secure API token.
    
    Returns:
        URL-safe token string prefixed with 'fs_'
    """
    return f"fs_{secrets.token_urlsafe(32)}"
