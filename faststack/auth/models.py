"""
FastStack Authentication Models

Provides the User model and related schemas for authentication.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import EmailStr, field_validator
from sqlmodel import Field, Relationship, SQLModel, Column, String, Boolean, DateTime

from faststack.orm.base import TimestampMixin

if TYPE_CHECKING:
    pass


class User(SQLModel, TimestampMixin, table=True):
    """
    User model for authentication.

    Stores user credentials and profile information.
    """

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(
        sa_column=Column(String(255), unique=True, index=True),
        description="User email address",
    )
    password_hash: str = Field(
        sa_column=Column(String(255)),
        description="Hashed password",
    )
    is_admin: bool = Field(default=False, description="Admin user flag")
    is_active: bool = Field(default=True, description="Active user flag")
    is_verified: bool = Field(default=False, description="Email verified flag")

    # Profile fields
    first_name: str | None = Field(default=None, sa_column=Column(String(100)))
    last_name: str | None = Field(default=None, sa_column=Column(String(100)))

    # Timestamps
    last_login: datetime | None = Field(default=None)

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.email.split("@")[0]

    @property
    def display_name(self) -> str:
        """Get the user's display name."""
        return self.full_name or self.email


class UserCreate(SQLModel):
    """Schema for creating a new user."""

    email: EmailStr
    password: str
    first_name: str | None = None
    last_name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(SQLModel):
    """Schema for updating user information."""

    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None


class UserRead(SQLModel):
    """Schema for reading user data (excludes sensitive fields)."""

    id: int
    email: str
    is_admin: bool
    is_active: bool
    first_name: str | None
    last_name: str | None
    full_name: str
    created_at: datetime
    last_login: datetime | None


class UserLogin(SQLModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class PasswordChange(SQLModel):
    """Schema for password change."""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class Token(SQLModel):
    """Schema for authentication token."""

    access_token: str
    token_type: str = "bearer"
