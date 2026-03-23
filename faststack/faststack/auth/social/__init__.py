"""
FastStack Social Authentication Module

Provides OAuth/OAuth2 authentication with popular providers:
- Google
- GitHub
- Facebook
- Microsoft
- Twitter
- Custom OAuth2 providers

Features:
- OAuth2 authorization code flow
- OAuth1 (for Twitter legacy)
- OpenID Connect support
- User profile extraction
- Account linking
- Multiple social accounts per user

Example:
    # settings.py
    SOCIAL_AUTH_ENABLED = True
    SOCIAL_AUTH_PROVIDERS = {
        'google': {
            'CLIENT_ID': 'xxx.apps.googleusercontent.com',
            'CLIENT_SECRET': 'yyy',
            'SCOPE': ['openid', 'email', 'profile'],
        },
        'github': {
            'CLIENT_ID': 'xxx',
            'CLIENT_SECRET': 'yyy',
        },
    }
    
    # In template
    <a href="/auth/social/google/">Sign in with Google</a>
"""

from faststack.auth.social.base import (
    OAuthProvider,
    OAuth2Provider,
    SocialAccount,
    SocialLogin,
)
from faststack.auth.social.manager import SocialAuthManager
from faststack.auth.social.adapter import SocialAccountAdapter

__all__ = [
    "OAuthProvider",
    "OAuth2Provider",
    "SocialAccount",
    "SocialLogin",
    "SocialAuthManager",
    "SocialAccountAdapter",
]
