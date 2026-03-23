"""
Social Account Adapter

Customizable adapter for social authentication behavior.
"""

from typing import Any
from abc import ABC, abstractmethod

from faststack.auth.social.base import SocialLogin, SocialAccount


class SocialAccountAdapter(ABC):
    """
    Abstract adapter for customizing social authentication behavior.
    
    Override methods to customize:
    - User creation from social login
    - User data population
    - Account connection
    - Pre/post login hooks
    """
    
    @abstractmethod
    async def pre_social_login(self, request: Any, social_login: SocialLogin) -> None:
        """
        Hook called before social login is processed.
        
        Use to:
        - Add extra data to social_login
        - Validate the social login
        - Add custom logic before login
        
        Args:
            request: HTTP request
            social_login: Social login data
        """
        pass
    
    @abstractmethod
    async def populate_user(self, user: Any, social_login: SocialLogin) -> None:
        """
        Populate user instance from social login data.
        
        Called when creating a new user or connecting an account.
        
        Args:
            user: User instance to populate
            social_login: Social login data
        """
        pass
    
    @abstractmethod
    async def get_user(self, social_login: SocialLogin, session: Any) -> Any | None:
        """
        Get existing user for social login.
        
        Default implementation finds by email.
        Override to change lookup behavior.
        
        Args:
            social_login: Social login data
            session: Database session
        
        Returns:
            User instance or None
        """
        pass
    
    @abstractmethod
    async def new_user(self, request: Any, social_login: SocialLogin, session: Any) -> Any:
        """
        Create a new user from social login.
        
        Args:
            request: HTTP request
            social_login: Social login data
            session: Database session
        
        Returns:
            New user instance
        """
        pass
    
    @abstractmethod
    async def save_user(self, user: Any, session: Any) -> None:
        """
        Save user to database.
        
        Args:
            user: User instance
            session: Database session
        """
        pass
    
    @abstractmethod
    async def is_auto_signup_allowed(self, request: Any, social_login: SocialLogin) -> bool:
        """
        Check if automatic signup is allowed.
        
        Override to add conditions for auto signup.
        
        Args:
            request: HTTP request
            social_login: Social login data
        
        Returns:
            True if auto signup is allowed
        """
        pass
    
    @abstractmethod
    async def is_open_for_signup(self, request: Any, social_login: SocialLogin) -> bool:
        """
        Check if signup is open for this provider.
        
        Args:
            request: HTTP request
            social_login: Social login data
        
        Returns:
            True if signup is open
        """
        pass


class DefaultSocialAccountAdapter(SocialAccountAdapter):
    """
    Default implementation of the social account adapter.
    
    Provides standard behavior for social authentication.
    """
    
    async def pre_social_login(self, request: Any, social_login: SocialLogin) -> None:
        """Default: no-op."""
        pass
    
    async def populate_user(self, user: Any, social_login: SocialLogin) -> None:
        """
        Populate user from social login.
        
        Sets email, name, and avatar if available.
        """
        if social_login.email and hasattr(user, 'email'):
            user.email = social_login.email
        
        if social_login.name and hasattr(user, 'name'):
            user.name = social_login.name
        
        if social_login.first_name and hasattr(user, 'first_name'):
            user.first_name = social_login.first_name
        
        if social_login.last_name and hasattr(user, 'last_name'):
            user.last_name = social_login.last_name
        
        if social_login.picture and hasattr(user, 'avatar_url'):
            user.avatar_url = social_login.picture
        
        # Mark email as verified for social logins
        if hasattr(user, 'email_verified'):
            user.email_verified = True
        
        # Activate user
        if hasattr(user, 'is_active'):
            user.is_active = True
    
    async def get_user(self, social_login: SocialLogin, session: Any) -> Any | None:
        """Find user by email."""
        if not social_login.email:
            return None
        
        from sqlmodel import select
        from faststack.auth.models import User
        
        statement = select(User).where(User.email == social_login.email)
        return session.exec(statement).first()
    
    async def new_user(self, request: Any, social_login: SocialLogin, session: Any) -> Any:
        """Create a new user from social login."""
        from faststack.auth.models import User
        from faststack.auth.utils import hash_password
        import secrets
        
        # Generate random password
        password = secrets.token_urlsafe(32)
        
        user = User(
            email=social_login.email,
            password_hash=hash_password(password),
            is_active=True,
            email_verified=True,
        )
        
        # Populate from social login
        await self.populate_user(user, social_login)
        
        return user
    
    async def save_user(self, user: Any, session: Any) -> None:
        """Save user to database."""
        session.add(user)
        session.commit()
        session.refresh(user)
    
    async def is_auto_signup_allowed(self, request: Any, social_login: SocialLogin) -> bool:
        """Default: always allow auto signup."""
        return True
    
    async def is_open_for_signup(self, request: Any, social_login: SocialLogin) -> bool:
        """Default: always open for signup."""
        from faststack.config import settings
        return getattr(settings, 'SOCIAL_AUTH_AUTO_SIGNUP', True)


# Adapter for email confirmation workflow
class EmailConfirmationSocialAdapter(DefaultSocialAccountAdapter):
    """
    Adapter that sends email confirmation for social signups.
    """
    
    async def new_user(self, request: Any, social_login: SocialLogin, session: Any) -> Any:
        """Create user and set email verification status."""
        user = await super().new_user(request, social_login, session)
        
        # For social logins, email is already verified by provider
        if hasattr(user, 'email_verified'):
            user.email_verified = True
        
        return user


# Adapter for passwordless accounts
class PasswordlessSocialAdapter(DefaultSocialAccountAdapter):
    """
    Adapter for passwordless social accounts.
    
    Users created through social auth won't have passwords set,
    and will need to use social auth or set a password later.
    """
    
    async def new_user(self, request: Any, social_login: SocialLogin, session: Any) -> Any:
        """Create user without password."""
        from faststack.auth.models import User
        
        user = User(
            email=social_login.email,
            password_hash='',  # No password
            is_active=True,
            email_verified=True,
        )
        
        await self.populate_user(user, social_login)
        
        return user
    
    async def is_auto_signup_allowed(self, request: Any, social_login: SocialLogin) -> bool:
        """Only allow if email is provided."""
        return bool(social_login.email)
