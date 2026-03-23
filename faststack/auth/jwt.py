"""
FastStack JWT Authentication Module

Provides JWT token generation and validation for API authentication.
"""

import secrets
from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlmodel import Session

from faststack.config import settings
from faststack.database import get_engine


class TokenData(BaseModel):
    """Data contained in a JWT token."""
    sub: str  # Subject (usually user ID)
    exp: datetime | None = None
    iat: datetime | None = None
    iss: str | None = None
    aud: str | None = None
    type: str = "access"  # access or refresh
    scope: list[str] = []


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class JWTManager:
    """
    JWT token manager for creating and validating tokens.
    """

    def __init__(
        self,
        secret_key: str | None = None,
        algorithm: str | None = None,
        access_token_expire_minutes: int | None = None,
        refresh_token_expire_days: int | None = None,
        issuer: str | None = None,
        audience: str | None = None,
    ):
        """
        Initialize JWT manager.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token expiry
            refresh_token_expire_days: Refresh token expiry
            issuer: Token issuer
            audience: Token audience
        """
        self.secret_key = secret_key or settings.JWT_SECRET_KEY or settings.SECRET_KEY
        self.algorithm = algorithm or settings.JWT_ALGORITHM
        self.access_token_expire_minutes = access_token_expire_minutes or settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = refresh_token_expire_days or settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        self.issuer = issuer or settings.JWT_ISSUER
        self.audience = audience or settings.JWT_AUDIENCE

    def create_access_token(
        self,
        subject: str,
        expires_delta: timedelta | None = None,
        additional_claims: dict[str, Any] | None = None,
        **kwargs,
    ) -> str:
        """
        Create a new access token.

        Args:
            subject: Token subject (usually user ID)
            expires_delta: Custom expiry time
            additional_claims: Additional claims to include
            **kwargs: Additional claims as keyword arguments

        Returns:
            Encoded JWT token
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)

        now = datetime.utcnow()
        expire = now + expires_delta

        to_encode = {
            "sub": subject,
            "exp": expire,
            "iat": now,
            "iss": self.issuer,
            "aud": self.audience,
            "type": "access",
        }

        if additional_claims:
            to_encode.update(additional_claims)
        
        # Add any extra kwargs as claims
        if kwargs:
            to_encode.update(kwargs)

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        subject: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """
        Create a new refresh token.

        Args:
            subject: Token subject (usually user ID)
            expires_delta: Custom expiry time

        Returns:
            Encoded JWT refresh token
        """
        if expires_delta is None:
            expires_delta = timedelta(days=self.refresh_token_expire_days)

        now = datetime.utcnow()
        expire = now + expires_delta

        to_encode = {
            "sub": subject,
            "exp": expire,
            "iat": now,
            "iss": self.issuer,
            "aud": self.audience,
            "type": "refresh",
        }

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_token_pair(self, subject: str, additional_claims: dict[str, Any] | None = None) -> Token:
        """
        Create both access and refresh tokens.

        Args:
            subject: Token subject (usually user ID)
            additional_claims: Additional claims for access token

        Returns:
            Token model with both tokens
        """
        access_token = self.create_access_token(subject, additional_claims=additional_claims)
        refresh_token = self.create_refresh_token(subject)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60,
        )

    def decode_token(self, token: str) -> TokenData:
        """
        Decode and validate a JWT token.

        Args:
            token: Encoded JWT token

        Returns:
            TokenData with decoded claims

        Raises:
            HTTPException: If token is invalid or expired
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
            )

            token_data = TokenData(
                sub=payload.get("sub", ""),
                exp=datetime.fromtimestamp(payload.get("exp", 0)),
                iat=datetime.fromtimestamp(payload.get("iat", 0)),
                iss=payload.get("iss"),
                aud=payload.get("aud"),
                type=payload.get("type", "access"),
                scope=payload.get("scope", []),
            )

            return token_data

        except JWTError:
            raise credentials_exception

    def validate_token(self, token: str, token_type: str = "access") -> TokenData:
        """
        Validate a token and check its type.

        Args:
            token: Encoded JWT token
            token_type: Expected token type (access or refresh)

        Returns:
            TokenData if valid

        Raises:
            HTTPException: If token is invalid
        """
        token_data = self.decode_token(token)

        if token_data.type != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type, expected {token_type}",
            )

        return token_data


# Global JWT manager instance
_jwt_manager: JWTManager | None = None


def get_jwt_manager() -> JWTManager:
    """Get the global JWT manager instance."""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


# Security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """
    Get current user ID from JWT token.

    Args:
        credentials: Bearer token credentials

    Returns:
        User ID from token

    Raises:
        HTTPException: If token is missing or invalid
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwt_manager = get_jwt_manager()
    token_data = jwt_manager.validate_token(credentials.credentials)

    return token_data.sub


async def get_optional_user_from_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    """
    Get current user ID from JWT token if present.

    Args:
        credentials: Bearer token credentials

    Returns:
        User ID from token or None
    """
    if credentials is None:
        return None

    try:
        jwt_manager = get_jwt_manager()
        token_data = jwt_manager.validate_token(credentials.credentials)
        return token_data.sub
    except HTTPException:
        return None


def generate_api_key() -> str:
    """
    Generate a secure API key.

    Returns:
        URL-safe API key string
    """
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.

    Args:
        api_key: Plain API key

    Returns:
        Hashed API key
    """
    import hashlib
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.

    Args:
        api_key: Plain API key
        hashed_key: Hashed API key

    Returns:
        True if key matches
    """
    return hash_api_key(api_key) == hashed_key
