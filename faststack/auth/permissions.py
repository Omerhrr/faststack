"""
FastStack Permissions System

Provides utilities for managing groups, permissions, and access control.
"""

from datetime import datetime, timedelta
from typing import Optional
import secrets

from sqlmodel import Session, select

from faststack.auth.models import (
    User, Group, Permission, UserGroup, UserPermission, GroupPermission,
    PasswordResetToken, PasswordHistory, APIToken, AuditLog,
)
from faststack.config import settings


# =============================================================================
# Permission Utilities
# =============================================================================

def create_permission(
    session: Session,
    name: str,
    codename: str,
    app_label: str,
    action: str,
    model: str,
    description: str | None = None,
) -> Permission:
    """
    Create a new permission.
    
    Args:
        session: Database session
        name: Human readable name
        codename: Permission code (e.g., 'blog.add_post')
        app_label: App name (e.g., 'blog')
        action: Action type (add, change, delete, view)
        model: Model name (e.g., 'post')
        description: Optional description
    
    Returns:
        Created Permission instance
    """
    permission = Permission(
        name=name,
        codename=codename,
        app_label=app_label,
        action=action,
        model=model,
        description=description,
    )
    session.add(permission)
    session.commit()
    session.refresh(permission)
    return permission


def get_or_create_permission(
    session: Session,
    codename: str,
    name: str,
    app_label: str,
    action: str,
    model: str,
) -> Permission:
    """Get existing permission or create new one."""
    existing = session.exec(
        select(Permission).where(Permission.codename == codename)
    ).first()
    
    if existing:
        return existing
    
    return create_permission(
        session=session,
        name=name,
        codename=codename,
        app_label=app_label,
        action=action,
        model=model,
    )


def assign_permission_to_user(
    session: Session,
    user: User,
    permission: Permission | str,
) -> bool:
    """
    Assign a permission to a user.
    
    Args:
        session: Database session
        user: User instance
        permission: Permission instance or codename
    
    Returns:
        True if permission was assigned
    """
    if isinstance(permission, str):
        perm = session.exec(
            select(Permission).where(Permission.codename == permission)
        ).first()
        if not perm:
            return False
        permission = perm
    
    # Check if already assigned
    existing = session.exec(
        select(UserPermission).where(
            UserPermission.user_id == user.id,
            UserPermission.permission_id == permission.id,
        )
    ).first()
    
    if existing:
        return True
    
    user_perm = UserPermission(user_id=user.id, permission_id=permission.id)
    session.add(user_perm)
    session.commit()
    return True


def remove_permission_from_user(
    session: Session,
    user: User,
    permission: Permission | str,
) -> bool:
    """Remove a permission from a user."""
    if isinstance(permission, str):
        perm = session.exec(
            select(Permission).where(Permission.codename == permission)
        ).first()
        if not perm:
            return False
        permission = perm
    
    user_perm = session.exec(
        select(UserPermission).where(
            UserPermission.user_id == user.id,
            UserPermission.permission_id == permission.id,
        )
    ).first()
    
    if user_perm:
        session.delete(user_perm)
        session.commit()
        return True
    
    return False


def user_has_permission(session: Session, user: User, permission: str) -> bool:
    """
    Check if a user has a specific permission.
    
    Args:
        session: Database session
        user: User instance
        permission: Permission codename
    
    Returns:
        True if user has permission
    """
    if user.is_superuser:
        return True
    
    # Check user permissions
    user_perm = session.exec(
        select(UserPermission)
        .join(Permission)
        .where(
            UserPermission.user_id == user.id,
            Permission.codename == permission,
        )
    ).first()
    
    if user_perm:
        return True
    
    # Check group permissions
    group_perm = session.exec(
        select(GroupPermission)
        .join(Group)
        .join(UserGroup)
        .join(Permission)
        .where(
            UserGroup.user_id == user.id,
            Permission.codename == permission,
        )
    ).first()
    
    return group_perm is not None


# =============================================================================
# Group Utilities
# =============================================================================

def create_group(
    session: Session,
    name: str,
    description: str | None = None,
) -> Group:
    """Create a new group."""
    group = Group(name=name, description=description)
    session.add(group)
    session.commit()
    session.refresh(group)
    return group


def add_user_to_group(
    session: Session,
    user: User,
    group: Group | str,
) -> bool:
    """Add a user to a group."""
    if isinstance(group, str):
        grp = session.exec(
            select(Group).where(Group.name == group)
        ).first()
        if not grp:
            return False
        group = grp
    
    existing = session.exec(
        select(UserGroup).where(
            UserGroup.user_id == user.id,
            UserGroup.group_id == group.id,
        )
    ).first()
    
    if existing:
        return True
    
    user_group = UserGroup(user_id=user.id, group_id=group.id)
    session.add(user_group)
    session.commit()
    return True


def remove_user_from_group(
    session: Session,
    user: User,
    group: Group | str,
) -> bool:
    """Remove a user from a group."""
    if isinstance(group, str):
        grp = session.exec(
            select(Group).where(Group.name == group)
        ).first()
        if not grp:
            return False
        group = grp
    
    user_group = session.exec(
        select(UserGroup).where(
            UserGroup.user_id == user.id,
            UserGroup.group_id == group.id,
        )
    ).first()
    
    if user_group:
        session.delete(user_group)
        session.commit()
        return True
    
    return False


def assign_permission_to_group(
    session: Session,
    group: Group | str,
    permission: Permission | str,
) -> bool:
    """Assign a permission to a group."""
    if isinstance(group, str):
        grp = session.exec(
            select(Group).where(Group.name == group)
        ).first()
        if not grp:
            return False
        group = grp
    
    if isinstance(permission, str):
        perm = session.exec(
            select(Permission).where(Permission.codename == permission)
        ).first()
        if not perm:
            return False
        permission = perm
    
    existing = session.exec(
        select(GroupPermission).where(
            GroupPermission.group_id == group.id,
            GroupPermission.permission_id == permission.id,
        )
    ).first()
    
    if existing:
        return True
    
    group_perm = GroupPermission(group_id=group.id, permission_id=permission.id)
    session.add(group_perm)
    session.commit()
    return True


# =============================================================================
# Password Reset Utilities
# =============================================================================

def create_password_reset_token(
    session: Session,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
    expires_hours: int | None = None,
) -> PasswordResetToken:
    """
    Create a password reset token for a user.
    
    Args:
        session: Database session
        user: User instance
        ip_address: Request IP address
        user_agent: Request user agent
        expires_hours: Hours until expiration (default: from settings)
    
    Returns:
        PasswordResetToken instance
    """
    expires_hours = expires_hours or settings.PASSWORD_RESET_EXPIRE_HOURS
    
    token = PasswordResetToken(
        user_id=user.id,
        token=PasswordResetToken.generate_token(),
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    session.add(token)
    session.commit()
    session.refresh(token)
    
    return token


def validate_password_reset_token(
    session: Session,
    token: str,
) -> User | None:
    """
    Validate a password reset token.
    
    Args:
        session: Database session
        token: Token string
    
    Returns:
        User if token is valid, None otherwise
    """
    reset_token = session.exec(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    ).first()
    
    if not reset_token:
        return None
    
    if not reset_token.is_valid:
        return None
    
    return session.get(User, reset_token.user_id)


def use_password_reset_token(
    session: Session,
    token: str,
) -> bool:
    """
    Mark a password reset token as used.
    
    Args:
        session: Database session
        token: Token string
    
    Returns:
        True if token was marked as used
    """
    reset_token = session.exec(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    ).first()
    
    if not reset_token:
        return False
    
    reset_token.used_at = datetime.utcnow()
    session.add(reset_token)
    session.commit()
    return True


def cleanup_expired_reset_tokens(session: Session) -> int:
    """
    Delete expired password reset tokens.
    
    Returns:
        Number of tokens deleted
    """
    expired = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.expires_at < datetime.utcnow()
        )
    ).all()
    
    count = len(expired)
    for token in expired:
        session.delete(token)
    
    session.commit()
    return count


# =============================================================================
# Password History Utilities
# =============================================================================

def add_to_password_history(
    session: Session,
    user: User,
    password_hash: str,
) -> None:
    """Add a password hash to user's history."""
    history = PasswordHistory(
        user_id=user.id,
        password_hash=password_hash,
    )
    session.add(history)
    session.commit()


def is_password_in_history(
    session: Session,
    user: User,
    password: str,
    count: int | None = None,
) -> bool:
    """
    Check if password is in user's recent history.
    
    Args:
        session: Database session
        user: User instance
        password: Plain text password
        count: Number of recent passwords to check
    
    Returns:
        True if password was recently used
    """
    from faststack.auth.utils import verify_password
    
    count = count or settings.PASSWORD_HISTORY_COUNT
    
    if count <= 0:
        return False
    
    history = session.exec(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(count)
    ).all()
    
    for entry in history:
        if verify_password(password, entry.password_hash):
            return True
    
    return False


def cleanup_password_history(
    session: Session,
    user: User,
    keep_count: int | None = None,
) -> int:
    """
    Remove old password history entries.
    
    Returns:
        Number of entries removed
    """
    keep_count = keep_count or settings.PASSWORD_HISTORY_COUNT
    
    history = session.exec(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.created_at.desc())
    ).all()
    
    removed = 0
    for i, entry in enumerate(history):
        if i >= keep_count:
            session.delete(entry)
            removed += 1
    
    session.commit()
    return removed


# =============================================================================
# API Token Utilities
# =============================================================================

def create_api_token(
    session: Session,
    user: User,
    name: str,
    expires_at: datetime | None = None,
    scopes: str | None = None,
) -> tuple[APIToken, str]:
    """
    Create an API token for a user.
    
    Args:
        session: Database session
        user: User instance
        name: Token name
        expires_at: Optional expiration date
        scopes: Optional comma-separated scopes
    
    Returns:
        Tuple of (APIToken instance, raw token string)
    """
    raw_token = APIToken.generate_token()
    
    token = APIToken(
        user_id=user.id,
        name=name,
        token=raw_token,
        token_prefix=raw_token[:8],
        expires_at=expires_at,
        scopes=scopes or "",
    )
    
    session.add(token)
    session.commit()
    session.refresh(token)
    
    return token, raw_token


def validate_api_token(
    session: Session,
    token: str,
) -> User | None:
    """
    Validate an API token.
    
    Args:
        session: Database session
        token: Token string
    
    Returns:
        User if token is valid, None otherwise
    """
    api_token = session.exec(
        select(APIToken).where(APIToken.token == token)
    ).first()
    
    if not api_token:
        return None
    
    if not api_token.is_valid:
        return None
    
    # Update last used
    api_token.last_used_at = datetime.utcnow()
    session.add(api_token)
    session.commit()
    
    return session.get(User, api_token.user_id)


def revoke_api_token(
    session: Session,
    token: APIToken | str | int,
) -> bool:
    """Revoke an API token."""
    if isinstance(token, str):
        api_token = session.exec(
            select(APIToken).where(APIToken.token == token)
        ).first()
    elif isinstance(token, int):
        api_token = session.get(APIToken, token)
    else:
        api_token = token
    
    if not api_token:
        return False
    
    api_token.is_active = False
    session.add(api_token)
    session.commit()
    return True


def list_user_api_tokens(
    session: Session,
    user: User,
    include_revoked: bool = False,
) -> list[APIToken]:
    """List all API tokens for a user."""
    query = select(APIToken).where(APIToken.user_id == user.id)
    
    if not include_revoked:
        query = query.where(APIToken.is_active == True)
    
    return list(session.exec(query).all())


# =============================================================================
# Audit Log Utilities
# =============================================================================

def log_action(
    session: Session,
    action: str,
    user_id: int | None = None,
    model: str | None = None,
    model_id: int | None = None,
    changes: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> AuditLog:
    """
    Log an action to the audit log.
    
    Args:
        session: Database session
        action: Action type (login, logout, create, update, delete)
        user_id: User who performed the action
        model: Model name
        model_id: Model instance ID
        changes: JSON string of changes
        ip_address: Request IP
        user_agent: Request user agent
        success: Whether action succeeded
        error_message: Error message if failed
    
    Returns:
        AuditLog instance
    """
    import json
    
    log = AuditLog(
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
    
    session.add(log)
    session.commit()
    session.refresh(log)
    
    return log


def get_user_audit_logs(
    session: Session,
    user_id: int,
    limit: int = 100,
) -> list[AuditLog]:
    """Get audit logs for a user."""
    return list(session.exec(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    ).all())


def get_model_audit_logs(
    session: Session,
    model: str,
    model_id: int | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    """Get audit logs for a model."""
    query = select(AuditLog).where(AuditLog.model == model)
    
    if model_id:
        query = query.where(AuditLog.model_id == model_id)
    
    return list(session.exec(
        query.order_by(AuditLog.timestamp.desc()).limit(limit)
    ).all())


# =============================================================================
# Default Permissions Setup
# =============================================================================

def create_default_permissions(session: Session) -> list[Permission]:
    """
    Create default permissions for common actions.
    
    Creates permissions: add, change, delete, view for each model.
    """
    permissions = []
    
    # Common CRUD permissions template
    crud_actions = [
        ('add', 'Can add {model}'),
        ('change', 'Can change {model}'),
        ('delete', 'Can delete {model}'),
        ('view', 'Can view {model}'),
    ]
    
    # Default models to create permissions for
    default_models = [
        ('auth', 'user'),
        ('auth', 'group'),
        ('auth', 'permission'),
    ]
    
    for app_label, model in default_models:
        for action, name_template in crud_actions:
            codename = f"{app_label}.{action}_{model}"
            name = name_template.format(model=model.title())
            
            perm = get_or_create_permission(
                session=session,
                codename=codename,
                name=name,
                app_label=app_label,
                action=action,
                model=model,
            )
            permissions.append(perm)
    
    return permissions


def create_default_groups(session: Session) -> dict[str, Group]:
    """Create default groups with permissions."""
    groups = {}
    
    # Admin group - full access
    admin_group = create_group(
        session=session,
        name="Admins",
        description="Full administrative access",
    )
    groups['admin'] = admin_group
    
    # Editor group - can create and edit
    editor_group = create_group(
        session=session,
        name="Editors",
        description="Can create and edit content",
    )
    groups['editor'] = editor_group
    
    # Viewer group - read-only
    viewer_group = create_group(
        session=session,
        name="Viewers",
        description="Read-only access",
    )
    groups['viewer'] = viewer_group
    
    return groups
