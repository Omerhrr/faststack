"""
FastStack Authentication Backends

Pluggable authentication backends like Django.

Example:
    from faststack.auth.backends import (
        AuthenticationBackend,
        ModelBackend,
        TokenBackend,
        JWTBackend
    )

    # Configure backends
    AUTHENTICATION_BACKENDS = [
        'faststack.auth.backends.ModelBackend',
        'faststack.auth.backends.JWTBackend',
    ]
"""

from typing import Any, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import inspect


class BaseBackend(ABC):
    """
    Base class for authentication backends.
    """

    @abstractmethod
    async def authenticate(self, request: Any, **credentials) -> Optional[Any]:
        """
        Authenticate a user.

        Args:
            request: The request object
            **credentials: Authentication credentials (varies by backend)

        Returns:
            User object if authentication successful, None otherwise
        """
        pass

    async def get_user(self, user_id: Any) -> Optional[Any]:
        """
        Get a user by ID.

        Args:
            user_id: The user's primary key

        Returns:
            User object or None
        """
        return None

    def has_perm(self, user: Any, perm: str, obj: Any = None) -> bool:
        """
        Check if user has a permission.

        Args:
            user: User object
            perm: Permission string (e.g., 'app.add_model')
            obj: Object to check permission for (optional)

        Returns:
            True if user has permission
        """
        return False

    def has_module_perms(self, user: Any, app_label: str) -> bool:
        """
        Check if user has any permissions for a module.

        Args:
            user: User object
            app_label: Application label

        Returns:
            True if user has any permissions
        """
        return False

    def get_all_permissions(self, user: Any, obj: Any = None) -> set:
        """
        Get all permissions for a user.

        Args:
            user: User object
            obj: Object to check permissions for (optional)

        Returns:
            Set of permission strings
        """
        return set()

    def get_user_permissions(self, user: Any, obj: Any = None) -> set:
        """Get user-specific permissions."""
        return set()

    def get_group_permissions(self, user: Any, obj: Any = None) -> set:
        """Get group permissions for user."""
        return set()


class ModelBackend(BaseBackend):
    """
    Authenticate against FastStack's User model.

    This is the default authentication backend.

    Example:
        backend = ModelBackend()
        user = await backend.authenticate(request, username='john', password='secret')
    """

    user_model: type = None

    def __init__(self, user_model: type = None):
        """
        Initialize ModelBackend.

        Args:
            user_model: User model class (optional, will be auto-detected)
        """
        self._user_model = user_model

    @property
    def user_model(self) -> type:
        """Get the user model."""
        if self._user_model is None:
            # Try to import the default user model
            try:
                from ..models import User
                self._user_model = User
            except ImportError:
                pass
        return self._user_model

    async def authenticate(
        self,
        request: Any,
        username: str = None,
        password: str = None,
        **kwargs
    ) -> Optional[Any]:
        """
        Authenticate user with username and password.

        Args:
            request: Request object
            username: Username or email
            password: Password
            **kwargs: Additional credentials

        Returns:
            User object if authentication successful
        """
        if username is None or password is None:
            return None

        user = await self._get_user(username)

        if user is None:
            # Run default password hasher to prevent timing attacks
            await self._verify_password('dummy_password', 'dummy_hash')
            return None

        # Verify password
        if await self._verify_password(password, user.password):
            return user

        return None

    async def _get_user(self, username: str) -> Optional[Any]:
        """Get user by username or email."""
        if self.user_model is None:
            return None

        # Try to get by username
        try:
            user = await self.user_model.get(username=username)
            return user
        except:
            pass

        # Try to get by email
        try:
            user = await self.user_model.get(email=username)
            return user
        except:
            pass

        return None

    async def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
            return pwd_context.verify(password, hashed)
        except ImportError:
            import hashlib
            # Fallback to simple hash
            return hashed == hashlib.sha256(password.encode()).hexdigest()

    async def get_user(self, user_id: Any) -> Optional[Any]:
        """Get user by ID."""
        if self.user_model is None:
            return None

        try:
            return await self.user_model.get(id=user_id)
        except:
            return None

    def has_perm(self, user: Any, perm: str, obj: Any = None) -> bool:
        """Check if user has permission."""
        if not user.is_active:
            return False

        if user.is_superuser:
            return True

        return perm in self.get_all_permissions(user, obj)

    def get_all_permissions(self, user: Any, obj: Any = None) -> set:
        """Get all user permissions."""
        if not user.is_active:
            return set()

        if user.is_superuser:
            return self._get_all_permissions()

        permissions = set()

        # Get user permissions
        permissions.update(self.get_user_permissions(user, obj))

        # Get group permissions
        permissions.update(self.get_group_permissions(user, obj))

        return permissions

    def _get_all_permissions(self) -> set:
        """Get all possible permissions."""
        # This would scan all models for permissions
        return set()

    def get_user_permissions(self, user: Any, obj: Any = None) -> set:
        """Get direct user permissions."""
        if hasattr(user, 'user_permissions'):
            return {f'{p.app_label}.{p.codename}' for p in user.user_permissions}
        return set()

    def get_group_permissions(self, user: Any, obj: Any = None) -> set:
        """Get group permissions."""
        if hasattr(user, 'groups'):
            permissions = set()
            for group in user.groups:
                if hasattr(group, 'permissions'):
                    permissions.update(
                        f'{p.app_label}.{p.codename}' for p in group.permissions
                    )
            return permissions
        return set()


class TokenBackend(BaseBackend):
    """
    Authenticate using API tokens.

    Example:
        backend = TokenBackend()
        user = await backend.authenticate(request, token='abc123')
    """

    token_model: type = None

    def __init__(self, token_model: type = None):
        self._token_model = token_model

    @property
    def token_model(self) -> type:
        """Get the token model."""
        if self._token_model is None:
            try:
                from ..models import Token
                self._token_model = Token
            except ImportError:
                pass
        return self._token_model

    async def authenticate(
        self,
        request: Any,
        token: str = None,
        **kwargs
    ) -> Optional[Any]:
        """
        Authenticate with API token.

        Args:
            request: Request object
            token: API token string

        Returns:
            User object if valid token
        """
        if token is None:
            return None

        if self.token_model is None:
            return None

        try:
            token_obj = await self.token_model.get(key=token)

            # Check if token is valid
            if not token_obj.is_valid():
                return None

            return await token_obj.user

        except:
            return None


class JWTBackend(BaseBackend):
    """
    Authenticate using JWT tokens.

    Example:
        backend = JWTBackend()
        user = await backend.authenticate(request, token='eyJ0eXAiOiJKV1QiLCJhbGc...')
    """

    def __init__(
        self,
        secret_key: str = None,
        algorithm: str = 'HS256',
        access_token_lifetime: int = 3600,
        refresh_token_lifetime: int = 86400 * 7
    ):
        """
        Initialize JWTBackend.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm
            access_token_lifetime: Access token lifetime in seconds
            refresh_token_lifetime: Refresh token lifetime in seconds
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_lifetime = access_token_lifetime
        self.refresh_token_lifetime = refresh_token_lifetime

    async def authenticate(
        self,
        request: Any,
        token: str = None,
        **kwargs
    ) -> Optional[Any]:
        """Authenticate with JWT token."""
        if token is None:
            return None

        # Decode token
        payload = self._decode_token(token)
        if payload is None:
            return None

        # Get user ID from payload
        user_id = payload.get('user_id') or payload.get('sub')
        if user_id is None:
            return None

        # Get user
        return await self.get_user(user_id)

    def _decode_token(self, token: str) -> Optional[dict]:
        """Decode JWT token."""
        try:
            import jwt
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.InvalidTokenError:
            return None

    async def get_user(self, user_id: Any) -> Optional[Any]:
        """Get user by ID."""
        try:
            from ..models import User
            return await User.get(id=user_id)
        except:
            return None

    def create_access_token(self, user: Any) -> str:
        """Create access token for user."""
        import jwt
        import time

        payload = {
            'user_id': user.id,
            'exp': int(time.time()) + self.access_token_lifetime,
            'iat': int(time.time()),
            'type': 'access'
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user: Any) -> str:
        """Create refresh token for user."""
        import jwt
        import time

        payload = {
            'user_id': user.id,
            'exp': int(time.time()) + self.refresh_token_lifetime,
            'iat': int(time.time()),
            'type': 'refresh'
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)


class RemoteUserBackend(BaseBackend):
    """
    Backend for authentication via request headers.

    Useful for SSO, proxy authentication, etc.

    Example:
        backend = RemoteUserBackend(header='X-Remote-User')
        user = await backend.authenticate(request)
    """

    header: str = 'X-Remote-User'
    create_unknown_user: bool = True

    def __init__(
        self,
        header: str = None,
        create_unknown_user: bool = True,
        user_model: type = None
    ):
        self.header = header or self.header
        self.create_unknown_user = create_unknown_user
        self._user_model = user_model

    @property
    def user_model(self) -> type:
        if self._user_model is None:
            try:
                from ..models import User
                self._user_model = User
            except ImportError:
                pass
        return self._user_model

    async def authenticate(self, request: Any, **credentials) -> Optional[Any]:
        """Authenticate from request header."""
        username = request.headers.get(self.header)

        if not username:
            return None

        user = await self._get_user(username)

        if user is None and self.create_unknown_user:
            user = await self._create_user(username)

        return user

    async def _get_user(self, username: str) -> Optional[Any]:
        """Get user by username."""
        if self.user_model is None:
            return None

        try:
            return await self.user_model.get(username=username)
        except:
            return None

    async def _create_user(self, username: str) -> Optional[Any]:
        """Create a new user."""
        if self.user_model is None:
            return None

        try:
            return await self.user_model.create(
                username=username,
                is_active=True
            )
        except:
            return None


class MultiFactorBackend(BaseBackend):
    """
    Backend for multi-factor authentication.

    Combines password authentication with MFA.
    """

    def __init__(self, primary_backend: BaseBackend = None):
        self.primary_backend = primary_backend or ModelBackend()

    async def authenticate(
        self,
        request: Any,
        username: str = None,
        password: str = None,
        otp: str = None,
        **kwargs
    ) -> Optional[Any]:
        """
        Authenticate with password and OTP.

        Args:
            request: Request object
            username: Username
            password: Password
            otp: One-time password from authenticator app
        """
        # First, authenticate with primary backend
        user = await self.primary_backend.authenticate(
            request,
            username=username,
            password=password,
            **kwargs
        )

        if user is None:
            return None

        # Check if MFA is enabled for user
        if not getattr(user, 'mfa_enabled', False):
            return user

        # Verify OTP
        if otp is None:
            # MFA required but not provided
            return None

        if await self._verify_otp(user, otp):
            return user

        return None

    async def _verify_otp(self, user: Any, otp: str) -> bool:
        """Verify one-time password."""
        try:
            import pyotp
            totp = pyotp.TOTP(user.mfa_secret)
            return totp.verify(otp, valid_window=1)
        except ImportError:
            return False


class AuthenticationMiddleware:
    """
    Middleware for authenticating requests using backends.
    """

    def __init__(
        self,
        app: Any,
        backends: List[BaseBackend] = None,
        user_model: type = None
    ):
        self.app = app
        self.backends = backends or [ModelBackend()]
        self.user_model = user_model

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # Get user from session or token
        user = await self._authenticate(scope)

        # Store user in scope
        scope['user'] = user

        await self.app(scope, receive, send)

    async def _authenticate(self, scope: Any) -> Optional[Any]:
        """Try to authenticate with each backend."""
        # Try session auth
        session = scope.get('session', {})
        user_id = session.get('user_id')

        if user_id:
            for backend in self.backends:
                user = await backend.get_user(user_id)
                if user:
                    return user

        return None


def get_user(request: Any) -> Any:
    """
    Get the current user from request.

    Args:
        request: Request object

    Returns:
        User object or AnonymousUser
    """
    user = getattr(request, 'user', None)

    if user is None:
        from .utils import AnonymousUser
        return AnonymousUser()

    return user
