"""
Session Middleware for FastStack.
"""

from typing import Any, Callable, Optional, Union
from starlette.types import ASGIApp, Receive, Scope, Send, Message
from starlette.requests import Request

from .backends import (
    SessionBase,
    SessionStore,
    DatabaseSessionStore,
    RedisSessionStore,
    CookieSessionStore,
    FileSessionStore,
    CacheSessionStore,
)


class SessionMiddleware:
    """
    Middleware for handling sessions.

    Adds a session attribute to each request.

    Example:
        app = FastStack()
        app.add_middleware(SessionMiddleware, secret_key='your-secret-key')

        # Use in route
        @app.route('/login')
        async def login(request):
            request.session['user_id'] = user.id
            return Response('OK')

        @app.route('/profile')
        async def profile(request):
            user_id = request.session.get('user_id')
            return Response(f'User: {user_id}')
    """

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str,
        session_cookie_name: str = 'sessionid',
        session_cookie_age: int = 60 * 60 * 24 * 7 * 2,  # 2 weeks
        session_cookie_path: str = '/',
        session_cookie_domain: Optional[str] = None,
        session_cookie_secure: bool = False,
        session_cookie_httponly: bool = True,
        session_cookie_samesite: str = 'Lax',
        backend: str = 'cookie',
        **backend_options
    ):
        """
        Initialize SessionMiddleware.

        Args:
            app: ASGI application
            secret_key: Secret key for signing sessions
            session_cookie_name: Name of session cookie
            session_cookie_age: Session lifetime in seconds
            session_cookie_path: Cookie path
            session_cookie_domain: Cookie domain
            session_cookie_secure: Set secure flag
            session_cookie_httponly: Set httponly flag
            session_cookie_samesite: SameSite attribute
            backend: Session backend ('cookie', 'database', 'redis', 'file', 'cache')
            **backend_options: Additional options for backend
        """
        self.app = app
        self.secret_key = secret_key
        self.session_cookie_name = session_cookie_name
        self.session_cookie_age = session_cookie_age
        self.session_cookie_path = session_cookie_path
        self.session_cookie_domain = session_cookie_domain
        self.session_cookie_secure = session_cookie_secure
        self.session_cookie_httponly = session_cookie_httponly
        self.session_cookie_samesite = session_cookie_samesite
        self.backend = backend
        self.backend_options = backend_options

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # Get request
        request = Request(scope, receive)

        # Create session store
        session = self._create_session(request)

        # Store session in scope
        scope['session'] = session

        # Send wrapper to set cookie on response
        session_cookie_value = None

        async def send_wrapper(message: Message) -> None:
            nonlocal session_cookie_value

            if message['type'] == 'http.response.start':
                # Get cookie value before response is sent
                if session.modified:
                    if isinstance(session, CookieSessionStore):
                        session_cookie_value = session.get_cookie_value()

            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))

                # Add session cookie if modified
                if session.modified:
                    if session_cookie_value is not None:
                        # Delete cookie if session is empty
                        if not session.keys():
                            cookie_value = ''
                            max_age = 0
                        else:
                            cookie_value = session_cookie_value
                            max_age = self.session_cookie_age

                        cookie = self._build_cookie(cookie_value, max_age)
                        headers.append((b'set-cookie', cookie.encode('latin-1')))

                message['headers'] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _create_session(self, request: Request) -> SessionBase:
        """Create a session store instance."""
        session_key = request.cookies.get(self.session_cookie_name)

        if self.backend == 'cookie':
            return CookieSessionStore(
                session_key=session_key,
                request_cookies=request.cookies,
                secret_key=self.secret_key,
                **self.backend_options
            )
        elif self.backend == 'database':
            return DatabaseSessionStore(
                session_key=session_key,
                secret_key=self.secret_key,
                **self.backend_options
            )
        elif self.backend == 'redis':
            return RedisSessionStore(
                session_key=session_key,
                secret_key=self.secret_key,
                **self.backend_options
            )
        elif self.backend == 'file':
            return FileSessionStore(
                session_key=session_key,
                secret_key=self.secret_key,
                **self.backend_options
            )
        elif self.backend == 'cache':
            return CacheSessionStore(
                session_key=session_key,
                secret_key=self.secret_key,
                **self.backend_options
            )
        else:
            return SessionStore(
                session_key=session_key,
                secret_key=self.secret_key
            )

    def _build_cookie(self, value: str, max_age: int) -> str:
        """Build Set-Cookie header value."""
        parts = [f'{self.session_cookie_name}={value}']

        if self.session_cookie_path:
            parts.append(f'Path={self.session_cookie_path}')

        if self.session_cookie_domain:
            parts.append(f'Domain={self.session_cookie_domain}')

        if max_age:
            parts.append(f'Max-Age={max_age}')

        if self.session_cookie_secure:
            parts.append('Secure')

        if self.session_cookie_httponly:
            parts.append('HttpOnly')

        if self.session_cookie_samesite:
            parts.append(f'SameSite={self.session_cookie_samesite}')

        return '; '.join(parts)


def get_session(request: Request) -> SessionBase:
    """
    Get session from request.

    Args:
        request: Starlette Request object

    Returns:
        Session store instance
    """
    return request.scope.get('session') or SessionStore()
