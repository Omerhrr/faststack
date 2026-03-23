"""
Social Authentication Manager

Manages social authentication flow and account linking.
"""

from typing import Any, Callable
from datetime import datetime

from faststack.auth.social.base import OAuth2Provider, SocialAccount, SocialLogin
from faststack.auth.social.providers import get_provider, PROVIDERS


class SocialAuthManager:
    """
    Manages social authentication.
    
    Handles:
    - Provider configuration
    - OAuth flow initiation
    - User creation/linking
    - Session management
    
    Example:
        manager = SocialAuthManager()
        
        # Get authorization URL
        url = manager.get_authorization_url('google', redirect_uri, state)
        
        # Complete login
        social_login = await manager.complete_login('google', code, redirect_uri)
        
        # Login or register user
        user = await manager.login(social_login)
    """
    
    def __init__(
        self,
        providers_config: dict[str, dict[str, Any]] | None = None,
        adapter: Any = None,
    ):
        """
        Initialize the social auth manager.
        
        Args:
            providers_config: Dict of provider_name -> config
            adapter: Optional adapter for custom behavior
        """
        self._providers: dict[str, OAuth2Provider] = {}
        self._adapter = adapter
        
        if providers_config:
            for name, config in providers_config.items():
                self.register_provider(name, config)
    
    def register_provider(
        self,
        name: str,
        config: dict[str, Any],
    ) -> None:
        """
        Register an OAuth provider.
        
        Args:
            name: Provider name
            config: Provider configuration
        """
        provider = get_provider(name, **config)
        self._providers[name] = provider
    
    def get_provider(self, name: str) -> OAuth2Provider:
        """
        Get a registered provider.
        
        Args:
            name: Provider name
        
        Returns:
            Provider instance
        
        Raises:
            ValueError: If provider not found
        """
        if name not in self._providers:
            raise ValueError(f"Provider '{name}' is not configured")
        return self._providers[name]
    
    def get_available_providers(self) -> list[str]:
        """Get list of registered provider names."""
        return list(self._providers.keys())
    
    def get_authorization_url(
        self,
        provider_name: str,
        redirect_uri: str,
        state: str,
    ) -> str:
        """
        Get the authorization URL for a provider.
        
        Args:
            provider_name: Provider name
            redirect_uri: Callback URI
            state: CSRF state
        
        Returns:
            Authorization URL
        """
        provider = self.get_provider(provider_name)
        return provider.get_authorization_url(redirect_uri, state)
    
    async def complete_login(
        self,
        provider_name: str,
        code: str,
        redirect_uri: str,
    ) -> SocialLogin:
        """
        Complete the OAuth login flow.
        
        Args:
            provider_name: Provider name
            code: Authorization code
            redirect_uri: Callback URI
        
        Returns:
            SocialLogin with user info
        """
        provider = self.get_provider(provider_name)
        return await provider.authenticate(code, redirect_uri)
    
    async def login(
        self,
        social_login: SocialLogin,
        session: Any,
        connect_existing: bool = True,
    ) -> tuple[Any, bool]:
        """
        Login or register a user from social login.
        
        Args:
            social_login: SocialLogin from provider
            session: Database session
            connect_existing: Whether to connect to existing user by email
        
        Returns:
            Tuple of (user, is_new_user)
        """
        # Look for existing social account
        account = await self._find_social_account(
            session,
            social_login.provider,
            social_login.provider_user_id,
        )
        
        if account:
            # Existing account - update and login
            user = await self._get_user(session, account.user_id)
            if user:
                # Update last login
                account.last_login = datetime.utcnow()
                session.add(account)
                session.commit()
                
                return user, False
        
        # No existing account - try to find by email
        if connect_existing and social_login.email:
            user = await self._find_user_by_email(session, social_login.email)
            
            if user:
                # Connect social account to existing user
                await self._connect_account(session, user, social_login)
                return user, False
        
        # Create new user
        user = await self._create_user(session, social_login)
        await self._connect_account(session, user, social_login)
        
        return user, True
    
    async def connect(
        self,
        user: Any,
        social_login: SocialLogin,
        session: Any,
    ) -> SocialAccount:
        """
        Connect a social account to an existing user.
        
        Args:
            user: Existing user
            social_login: SocialLogin from provider
            session: Database session
        
        Returns:
            Connected SocialAccount
        """
        return await self._connect_account(session, user, social_login)
    
    async def disconnect(
        self,
        user: Any,
        provider: str,
        session: Any,
    ) -> bool:
        """
        Disconnect a social account from a user.
        
        Args:
            user: User to disconnect from
            provider: Provider to disconnect
            session: Database session
        
        Returns:
            True if disconnected
        """
        from sqlmodel import select
        from faststack.auth.models import SocialAccount as SocialAccountModel
        
        statement = select(SocialAccountModel).where(
            SocialAccountModel.user_id == user.id,
            SocialAccountModel.provider == provider,
        )
        account = session.exec(statement).first()
        
        if account:
            session.delete(account)
            session.commit()
            return True
        
        return False
    
    async def _find_social_account(
        self,
        session: Any,
        provider: str,
        provider_user_id: str,
    ) -> SocialAccount | None:
        """Find an existing social account."""
        from sqlmodel import select
        from faststack.auth.models import SocialAccount as SocialAccountModel
        
        statement = select(SocialAccountModel).where(
            SocialAccountModel.provider == provider,
            SocialAccountModel.provider_user_id == str(provider_user_id),
        )
        
        return session.exec(statement).first()
    
    async def _get_user(self, session: Any, user_id: int) -> Any | None:
        """Get user by ID."""
        from faststack.auth.models import User
        return session.get(User, user_id)
    
    async def _find_user_by_email(self, session: Any, email: str) -> Any | None:
        """Find user by email."""
        from sqlmodel import select
        from faststack.auth.models import User
        
        statement = select(User).where(User.email == email)
        return session.exec(statement).first()
    
    async def _create_user(self, session: Any, social_login: SocialLogin) -> Any:
        """Create a new user from social login."""
        from faststack.auth.models import User
        from faststack.auth.utils import hash_password
        import secrets
        
        # Generate random password (user can set their own later)
        password = secrets.token_urlsafe(32)
        
        user = User(
            email=social_login.email,
            password_hash=hash_password(password),
            name=social_login.name,
            first_name=social_login.first_name,
            last_name=social_login.last_name,
            avatar_url=social_login.picture,
            is_active=True,
            email_verified=True,  # Social login emails are verified
        )
        
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return user
    
    async def _connect_account(
        self,
        session: Any,
        user: Any,
        social_login: SocialLogin,
    ) -> SocialAccount:
        """Connect a social account to a user."""
        from faststack.auth.models import SocialAccount as SocialAccountModel
        import json
        
        account = SocialAccountModel(
            user_id=user.id,
            provider=social_login.provider,
            provider_user_id=str(social_login.provider_user_id),
            extra_data=social_login.user_info,
            last_login=datetime.utcnow(),
        )
        
        session.add(account)
        session.commit()
        session.refresh(account)
        
        return account


# Global manager instance
_manager: SocialAuthManager | None = None


def get_social_auth_manager() -> SocialAuthManager:
    """Get the global social auth manager."""
    global _manager
    if _manager is None:
        from faststack.config import settings
        
        providers_config = getattr(settings, 'SOCIAL_AUTH_PROVIDERS', {})
        _manager = SocialAuthManager(providers_config=providers_config)
    
    return _manager
