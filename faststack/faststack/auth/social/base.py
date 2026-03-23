"""
Social Authentication Base Classes

Base classes for OAuth providers and social account models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class SocialAccount:
    """
    Represents a social account linked to a user.
    
    Attributes:
        provider: Provider name (google, github, etc.)
        provider_user_id: User ID from the provider
        user_id: Local user ID
        extra_data: Provider-specific user data
        created_at: When the account was linked
        last_login: Last login with this provider
    """
    provider: str
    provider_user_id: str
    user_id: int | None = None
    extra_data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    last_login: datetime | None = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class SocialLogin:
    """
    Represents an in-progress social login attempt.
    
    Contains the provider, user info from the provider, and any
    additional data needed to complete the login/registration.
    """
    provider: str
    user_info: dict[str, Any]
    account: SocialAccount | None = None
    token: dict[str, Any] | None = None
    
    @property
    def email(self) -> str | None:
        """Get email from user info."""
        return self.user_info.get('email')
    
    @property
    def name(self) -> str | None:
        """Get name from user info."""
        return self.user_info.get('name') or self.user_info.get('displayName')
    
    @property
    def first_name(self) -> str | None:
        """Get first name from user info."""
        return self.user_info.get('first_name') or self.user_info.get('given_name')
    
    @property
    def last_name(self) -> str | None:
        """Get last name from user info."""
        return self.user_info.get('last_name') or self.user_info.get('family_name')
    
    @property
    def picture(self) -> str | None:
        """Get profile picture URL from user info."""
        return self.user_info.get('picture') or self.user_info.get('avatar_url')
    
    @property
    def provider_user_id(self) -> str:
        """Get user ID from provider."""
        return str(self.user_info.get('id') or self.user_info.get('sub', ''))


class OAuthProvider(ABC):
    """
    Base class for OAuth providers.
    
    Defines the interface for OAuth authentication.
    """
    
    name: str = ""
    display_name: str = ""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scope: list[str] | None = None,
        redirect_uri: str | None = None,
        **kwargs,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope or self.get_default_scope()
        self.redirect_uri = redirect_uri
        self.options = kwargs
    
    @classmethod
    @abstractmethod
    def get_authorization_url(cls, redirect_uri: str, state: str) -> str:
        """
        Get the URL to redirect users for authorization.
        
        Args:
            redirect_uri: URI to redirect to after auth
            state: CSRF protection state
        
        Returns:
            Authorization URL
        """
        pass
    
    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from provider
            redirect_uri: Same redirect URI used in authorization
        
        Returns:
            Token dict (access_token, refresh_token, expires_in, etc.)
        """
        pass
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user info from the provider.
        
        Args:
            access_token: OAuth access token
        
        Returns:
            User info dict (id, email, name, etc.)
        """
        pass
    
    @classmethod
    def get_default_scope(cls) -> list[str]:
        """Get default OAuth scope."""
        return []
    
    def get_redirect_uri(self, request) -> str:
        """Get redirect URI for this provider."""
        if self.redirect_uri:
            return self.redirect_uri
        
        # Construct from request
        base_url = str(request.base_url).rstrip('/')
        return f"{base_url}/auth/social/{self.name}/callback/"
    
    async def authenticate(self, code: str, redirect_uri: str) -> SocialLogin:
        """
        Complete authentication flow.
        
        Args:
            code: Authorization code
            redirect_uri: Redirect URI
        
        Returns:
            SocialLogin with user info
        """
        # Exchange code for token
        token = await self.exchange_code(code, redirect_uri)
        
        # Get user info
        access_token = token.get('access_token')
        user_info = await self.get_user_info(access_token)
        
        # Create SocialLogin
        provider_user_id = str(user_info.get('id') or user_info.get('sub', ''))
        
        account = SocialAccount(
            provider=self.name,
            provider_user_id=provider_user_id,
            extra_data=user_info,
        )
        
        return SocialLogin(
            provider=self.name,
            user_info=user_info,
            account=account,
            token=token,
        )


class OAuth2Provider(OAuthProvider):
    """
    Base class for OAuth2 providers.
    
    Provides common OAuth2 flow implementation.
    """
    
    # URLs to override in subclasses
    authorization_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""
    
    @classmethod
    def get_authorization_url(cls, redirect_uri: str, state: str) -> str:
        """Build authorization URL with parameters."""
        from urllib.parse import urlencode
        
        params = {
            'client_id': cls.client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'state': state,
        }
        
        if cls.scope:
            params['scope'] = ' '.join(cls.scope)
        
        return f"{cls.authorization_url}?{urlencode(params)}"
    
    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange code for access token."""
        import httpx
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data=data,
                headers={'Accept': 'application/json'},
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user info from provider."""
        import httpx
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.userinfo_url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an access token.
        
        Args:
            refresh_token: OAuth refresh token
        
        Returns:
            New token dict
        """
        import httpx
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data=data,
                headers={'Accept': 'application/json'},
            )
            response.raise_for_status()
            return response.json()


class OpenIDConnectProvider(OAuth2Provider):
    """
    OpenID Connect provider.
    
    Extends OAuth2 with ID token verification.
    """
    
    jwks_url: str = ""
    issuer: str = ""
    
    async def verify_id_token(self, id_token: str) -> dict[str, Any]:
        """
        Verify and decode an ID token.
        
        Args:
            id_token: JWT ID token from provider
        
        Returns:
            Decoded token claims
        """
        from jose import jwt, jwk
        import httpx
        
        # Get JWKS
        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            jwks = response.json()
        
        # Decode header to get kid
        header = jwt.get_unverified_header(id_token)
        kid = header.get('kid')
        
        # Find matching key
        key = None
        for k in jwks.get('keys', []):
            if k.get('kid') == kid:
                key = jwk.construct(k)
                break
        
        if not key:
            raise ValueError("No matching key found for ID token")
        
        # Verify and decode
        claims = jwt.decode(
            id_token,
            key,
            algorithms=['RS256'],
            audience=self.client_id,
            issuer=self.issuer,
        )
        
        return claims
