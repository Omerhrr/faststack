"""
Social Auth Providers

Pre-configured OAuth2 providers for popular services.
"""

from typing import Any
from faststack.auth.social.base import OAuth2Provider, OpenIDConnectProvider


class GoogleProvider(OpenIDConnectProvider):
    """
    Google OAuth2 / OpenID Connect provider.
    
    Scopes:
        - openid: Required for ID token
        - email: Access to email
        - profile: Access to name, picture
    
    Example:
        provider = GoogleProvider(
            client_id='xxx.apps.googleusercontent.com',
            client_secret='yyy',
        )
    """
    
    name = 'google'
    display_name = 'Google'
    
    authorization_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    token_url = 'https://oauth2.googleapis.com/token'
    userinfo_url = 'https://openidconnect.googleapis.com/v1/userinfo'
    jwks_url = 'https://www.googleapis.com/oauth2/v3/certs'
    issuer = 'https://accounts.google.com'
    
    @classmethod
    def get_default_scope(cls) -> list[str]:
        return ['openid', 'email', 'profile']


class GitHubProvider(OAuth2Provider):
    """
    GitHub OAuth2 provider.
    
    Scopes:
        - user: Read user profile
        - user:email: Read user email
    
    Example:
        provider = GitHubProvider(
            client_id='xxx',
            client_secret='yyy',
        )
    """
    
    name = 'github'
    display_name = 'GitHub'
    
    authorization_url = 'https://github.com/login/oauth/authorize'
    token_url = 'https://github.com/login/oauth/access_token'
    userinfo_url = 'https://api.github.com/user'
    
    @classmethod
    def get_default_scope(cls) -> list[str]:
        return ['user', 'user:email']
    
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user info from GitHub."""
        import httpx
        
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/json',
        }
        
        async with httpx.AsyncClient() as client:
            # Get user info
            response = await client.get(self.userinfo_url, headers=headers)
            response.raise_for_status()
            user_info = response.json()
            
            # Get primary email if not public
            if not user_info.get('email'):
                email_response = await client.get(
                    'https://api.github.com/user/emails',
                    headers=headers,
                )
                if email_response.status_code == 200:
                    emails = email_response.json()
                    for email_data in emails:
                        if email_data.get('primary') and email_data.get('verified'):
                            user_info['email'] = email_data['email']
                            break
            
            return user_info


class FacebookProvider(OAuth2Provider):
    """
    Facebook OAuth2 provider.
    
    Scopes:
        - email: Access to email
        - public_profile: Access to name, picture
    
    Example:
        provider = FacebookProvider(
            client_id='xxx',
            client_secret='yyy',
        )
    """
    
    name = 'facebook'
    display_name = 'Facebook'
    
    authorization_url = 'https://www.facebook.com/v18.0/dialog/oauth'
    token_url = 'https://graph.facebook.com/v18.0/oauth/access_token'
    userinfo_url = 'https://graph.facebook.com/me'
    
    @classmethod
    def get_default_scope(cls) -> list[str]:
        return ['email', 'public_profile']
    
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user info from Facebook."""
        import httpx
        
        # Facebook requires fields to be specified
        fields = 'id,name,email,first_name,last_name,picture'
        url = f"{self.userinfo_url}?fields={fields}&access_token={access_token}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            user_info = response.json()
            
            # Normalize picture
            if 'picture' in user_info and 'data' in user_info['picture']:
                user_info['picture'] = user_info['picture']['data'].get('url')
            
            return user_info


class MicrosoftProvider(OpenIDConnectProvider):
    """
    Microsoft / Azure AD OAuth2 provider.
    
    Supports both personal Microsoft accounts and Azure AD.
    
    Scopes:
        - openid: Required for ID token
        - email: Access to email
        - profile: Access to name, picture
    
    Example:
        provider = MicrosoftProvider(
            client_id='xxx',
            client_secret='yyy',
            tenant='common',  # or 'organizations', 'consumers', or specific tenant
        )
    """
    
    name = 'microsoft'
    display_name = 'Microsoft'
    
    def __init__(self, tenant: str = 'common', **kwargs):
        self.tenant = tenant
        super().__init__(**kwargs)
        
        # Set URLs based on tenant
        self.authorization_url = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize'
        self.token_url = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
        self.jwks_url = f'https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys'
        self.issuer = f'https://login.microsoftonline.com/{tenant}/v2.0'
        self.userinfo_url = 'https://graph.microsoft.com/oidc/userinfo'
    
    @classmethod
    def get_default_scope(cls) -> list[str]:
        return ['openid', 'email', 'profile']


class TwitterProvider(OAuth2Provider):
    """
    Twitter OAuth2 provider (OAuth 2.0).
    
    Note: Twitter also supports OAuth 1.0a, but this implementation
    uses the newer OAuth 2.0 flow.
    
    Scopes:
        - users.read: Read user profile
        - tweet.read: Read tweets
    
    Example:
        provider = TwitterProvider(
            client_id='xxx',
            client_secret='yyy',
        )
    """
    
    name = 'twitter'
    display_name = 'Twitter'
    
    authorization_url = 'https://twitter.com/i/oauth2/authorize'
    token_url = 'https://api.twitter.com/2/oauth2/token'
    userinfo_url = 'https://api.twitter.com/2/users/me'
    
    @classmethod
    def get_default_scope(cls) -> list[str]:
        return ['users.read', 'tweet.read']
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Twitter requires PKCE
        self.code_challenge_method = 'S256'
    
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user info from Twitter."""
        import httpx
        
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        params = {
            'user.fields': 'id,name,username,profile_image_url,verified',
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_url,
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            
            # Twitter wraps in 'data'
            user_info = data.get('data', {})
            user_info['picture'] = user_info.pop('profile_image_url', None)
            
            return user_info


class AppleProvider(OAuth2Provider):
    """
    Apple Sign In provider.
    
    Scopes:
        - email: Access to email
        - name: Access to name
    
    Note: Apple only provides name on first sign-in.
    
    Example:
        provider = AppleProvider(
            client_id='com.example.app',
            client_secret='yyy',  # Generated JWT
        )
    """
    
    name = 'apple'
    display_name = 'Apple'
    
    authorization_url = 'https://appleid.apple.com/auth/authorize'
    token_url = 'https://appleid.apple.com/auth/token'
    
    @classmethod
    def get_default_scope(cls) -> list[str]:
        return ['email', 'name']
    
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user info from Apple ID token.
        
        Apple doesn't have a userinfo endpoint; all info is in the ID token.
        """
        from jose import jwt
        
        # Decode ID token (it's the access_token for Apple)
        claims = jwt.decode(
            access_token,
            options={'verify_signature': False},  # Should verify in production
        )
        
        return {
            'id': claims.get('sub'),
            'email': claims.get('email'),
            'email_verified': claims.get('email_verified'),
        }


class LinkedInProvider(OAuth2Provider):
    """
    LinkedIn OAuth2 provider.
    
    Scopes:
        - openid: Required for ID
        - profile: Access to name
        - email: Access to email
    
    Example:
        provider = LinkedInProvider(
            client_id='xxx',
            client_secret='yyy',
        )
    """
    
    name = 'linkedin'
    display_name = 'LinkedIn'
    
    authorization_url = 'https://www.linkedin.com/oauth/v2/authorization'
    token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
    userinfo_url = 'https://api.linkedin.com/v2/userinfo'
    
    @classmethod
    def get_default_scope(cls) -> list[str]:
        return ['openid', 'profile', 'email']


class DiscordProvider(OAuth2Provider):
    """
    Discord OAuth2 provider.
    
    Scopes:
        - identify: Access to username, avatar
        - email: Access to email
    
    Example:
        provider = DiscordProvider(
            client_id='xxx',
            client_secret='yyy',
        )
    """
    
    name = 'discord'
    display_name = 'Discord'
    
    authorization_url = 'https://discord.com/oauth2/authorize'
    token_url = 'https://discord.com/api/oauth2/token'
    userinfo_url = 'https://discord.com/api/users/@me'
    
    @classmethod
    def get_default_scope(cls) -> list[str]:
        return ['identify', 'email']
    
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user info from Discord."""
        import httpx
        
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.userinfo_url, headers=headers)
            response.raise_for_status()
            user_info = response.json()
            
            # Build avatar URL
            if user_info.get('avatar'):
                user_info['picture'] = (
                    f"https://cdn.discordapp.com/avatars/"
                    f"{user_info['id']}/{user_info['avatar']}.png"
                )
            
            return user_info


# Provider registry
PROVIDERS: dict[str, type[OAuth2Provider]] = {
    'google': GoogleProvider,
    'github': GitHubProvider,
    'facebook': FacebookProvider,
    'microsoft': MicrosoftProvider,
    'twitter': TwitterProvider,
    'apple': AppleProvider,
    'linkedin': LinkedInProvider,
    'discord': DiscordProvider,
}


def get_provider(name: str, **config) -> OAuth2Provider:
    """
    Get a provider instance by name.
    
    Args:
        name: Provider name (google, github, etc.)
        **config: Provider configuration (client_id, client_secret, etc.)
    
    Returns:
        Provider instance
    
    Raises:
        ValueError: If provider is not found
    """
    if name not in PROVIDERS:
        raise ValueError(f"Unknown OAuth provider: {name}")
    
    provider_class = PROVIDERS[name]
    return provider_class(**config)


def register_provider(name: str, provider_class: type[OAuth2Provider]) -> None:
    """
    Register a custom provider.
    
    Args:
        name: Provider name
        provider_class: Provider class
    """
    PROVIDERS[name] = provider_class
