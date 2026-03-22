"""
FastStack Auth Models

Provides User model, password reset tokens, groups, and permissions.
"""

from datetime import datetime
from typing import Optional
import secrets

from sqlmodel import Field, Relationship, SQLModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from faststack.auth.models import Group, Permission


class User(SQLModel, table=True):
    """
    User model for authentication and authorization.
    
    Attributes:
        email: Unique email address
        password_hash: Bcrypt hashed password
        first_name: Optional first name
        last_name: Optional last name
        is_active: Whether user can login
        is_admin: Whether user has admin access
        is_superuser: Whether user has all permissions
        last_login: Last successful login time
        created_at: Account creation time
        updated_at: Last update time
    """
    
    __tablename__ = "users"
    
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str = Field()
    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    is_superuser: bool = Field(default=False)
    last_login: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)
    
    # Relationships
    groups: list["Group"] = Relationship(back_populates="users", link_model="UserGroup")
    permissions: list["Permission"] = Relationship(back_populates="users", link_model="UserPermission")
    password_history: list["PasswordHistory"] = Relationship(back_populates="user")
    password_reset_tokens: list["PasswordResetToken"] = Relationship(back_populates="user")
    api_tokens: list["APIToken"] = Relationship(back_populates="user")
    
    @property
    def display_name(self) -> str:
        """Get display name for user."""
        if self.first_name or self.last_name:
            return f"{self.first_name or ''} {self.last_name or ''}".strip()
        return self.email
    
    def has_perm(self, permission: str) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            permission: Permission string (e.g., 'blog.add_post')
        
        Returns:
            True if user has permission
        """
        if self.is_superuser:
            return True
        
        # Check direct permissions
        for perm in self.permissions:
            if perm.codename == permission:
                return True
        
        # Check group permissions
        for group in self.groups:
            for perm in group.permissions:
                if perm.codename == permission:
                    return True
        
        return False
    
    def has_perms(self, permissions: list[str]) -> bool:
        """Check if user has all specified permissions."""
        return all(self.has_perm(p) for p in permissions)
    
    def get_all_permissions(self) -> set[str]:
        """Get all permission strings for user."""
        perms = set()
        
        for perm in self.permissions:
            perms.add(perm.codename)
        
        for group in self.groups:
            for perm in group.permissions:
                perms.add(perm.codename)
        
        return perms


class Group(SQLModel, table=True):
    """
    Group model for organizing users and permissions.
    
    Groups allow assigning permissions to multiple users at once.
    """
    
    __tablename__ = "auth_groups"
    
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    users: list["User"] = Relationship(back_populates="groups", link_model="UserGroup")
    permissions: list["Permission"] = Relationship(back_populates="groups", link_model="GroupPermission")


class Permission(SQLModel, table=True):
    """
    Permission model for fine-grained access control.
    
    Permissions follow Django-style naming: app.action_model
    Example: 'blog.add_post', 'blog.change_post', 'blog.delete_post'
    """
    
    __tablename__ = "auth_permissions"
    
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)  # Human readable name
    codename: str = Field(unique=True, index=True)  # 'blog.add_post'
    app_label: str = Field(index=True)  # 'blog'
    action: str = Field()  # 'add', 'change', 'delete', 'view'
    model: str = Field()  # 'post'
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    users: list["User"] = Relationship(back_populates="permissions", link_model="UserPermission")
    groups: list["Group"] = Relationship(back_populates="permissions", link_model="GroupPermission")


class UserGroup(SQLModel, table=True):
    """Many-to-many relationship between Users and Groups."""
    
    __tablename__ = "auth_user_groups"
    
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    group_id: int = Field(foreign_key="auth_groups.id", index=True)


class UserPermission(SQLModel, table=True):
    """Many-to-many relationship between Users and Permissions."""
    
    __tablename__ = "auth_user_permissions"
    
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    permission_id: int = Field(foreign_key="auth_permissions.id", index=True)


class GroupPermission(SQLModel, table=True):
    """Many-to-many relationship between Groups and Permissions."""
    
    __tablename__ = "auth_group_permissions"
    
    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="auth_groups.id", index=True)
    permission_id: int = Field(foreign_key="auth_permissions.id", index=True)


class PasswordResetToken(SQLModel, table=True):
    """
    Password reset token stored in database.
    
    More secure than session-based tokens as they can be:
    - Invalidated on use
    - Have expiration enforced server-side
    - Tracked for abuse
    """
    
    __tablename__ = "auth_password_reset_tokens"
    
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    token: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field()
    used_at: datetime | None = Field(default=None)
    ip_address: str | None = Field(default=None)
    user_agent: str | None = Field(default=None)
    
    # Relationships
    user: User = Relationship(back_populates="password_reset_tokens")
    
    @classmethod
    def generate_token(cls) -> str:
        """Generate a secure token."""
        return secrets.token_urlsafe(32)
    
    @property
    def is_used(self) -> bool:
        """Check if token has been used."""
        return self.used_at is not None
    
    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if token is still valid."""
        return not self.is_used and not self.is_expired


class PasswordHistory(SQLModel, table=True):
    """
    Password history for preventing reuse.
    
    Stores previous password hashes to prevent users from
    reusing recent passwords.
    """
    
    __tablename__ = "auth_password_history"
    
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    password_hash: str = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="password_history")


class APIToken(SQLModel, table=True):
    """
    Personal API access token for users.
    
    Allows users to generate tokens for API access without
    using their password.
    """
    
    __tablename__ = "auth_api_tokens"
    
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field()  # User-defined name
    token: str = Field(unique=True, index=True)  # The actual token
    token_prefix: str = Field(index=True)  # First 8 chars for identification
    is_active: bool = Field(default=True)
    last_used_at: datetime | None = Field(default=None)
    expires_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scopes: str = Field(default="")  # Comma-separated scopes
    
    # Relationships
    user: User = Relationship(back_populates="api_tokens")
    
    @classmethod
    def generate_token(cls) -> str:
        """Generate a secure API token."""
        return f"fs_{secrets.token_urlsafe(32)}"
    
    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return self.is_active and not self.is_expired
    
    def has_scope(self, scope: str) -> bool:
        """Check if token has a specific scope."""
        if not self.scopes:
            return True  # No scope restriction
        return scope in self.scopes.split(",")


class AuditLog(SQLModel, table=True):
    """
    Audit log for tracking user actions.
    
    Records important actions like login, logout, data changes.
    """
    
    __tablename__ = "auth_audit_log"
    
    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(foreign_key="users.id", index=True, nullable=True)
    action: str = Field(index=True)  # 'login', 'logout', 'create', 'update', 'delete'
    model: str | None = Field(default=None, index=True)  # Model name
    model_id: int | None = Field(default=None)  # Model instance ID
    changes: str | None = Field(default=None)  # JSON of changes
    ip_address: str | None = Field(default=None)
    user_agent: str | None = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    success: bool = Field(default=True)
    error_message: str | None = Field(default=None)
    
    @classmethod
    def log(
        cls,
        action: str,
        user_id: int | None = None,
        model: str | None = None,
        model_id: int | None = None,
        changes: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> "AuditLog":
        """Create an audit log entry."""
        return cls(
            user_id=user_id,
            action=action,
            model=model,
            model_id=model_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
        )


# Pydantic models for API

class UserCreate(SQLModel):
    """Schema for user registration."""
    email: str
    password: str
    first_name: str | None = None
    last_name: str | None = None


class UserLogin(SQLModel):
    """Schema for user login."""
    email: str
    password: str


class UserRead(SQLModel):
    """Schema for reading user data."""
    id: int
    email: str
    first_name: str | None
    last_name: str | None
    is_active: bool
    is_admin: bool
    display_name: str
    
    class Config:
        from_attributes = True


class GroupCreate(SQLModel):
    """Schema for creating a group."""
    name: str
    description: str | None = None


class GroupRead(SQLModel):
    """Schema for reading group data."""
    id: int
    name: str
    description: str | None
    
    class Config:
        from_attributes = True


class PermissionCreate(SQLModel):
    """Schema for creating a permission."""
    name: str
    codename: str
    app_label: str
    action: str
    model: str
    description: str | None = None


class PermissionRead(SQLModel):
    """Schema for reading permission data."""
    id: int
    name: str
    codename: str
    app_label: str
    action: str
    model: str
    
    class Config:
        from_attributes = True


class APITokenCreate(SQLModel):
    """Schema for creating an API token."""
    name: str
    expires_at: datetime | None = None
    scopes: str | None = None


class APITokenRead(SQLModel):
    """Schema for reading API token data."""
    id: int
    name: str
    token_prefix: str
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    scopes: str
    
    class Config:
        from_attributes = True
