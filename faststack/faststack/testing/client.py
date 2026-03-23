"""
Test Client

HTTP client for testing FastStack applications.
"""

import json
from typing import Any
from contextlib import asynccontextmanager
from dataclasses import dataclass
from http.cookies import SimpleCookie

import httpx


@dataclass
class Response:
    """
    Response wrapper for test assertions.
    
    Provides convenient access to response data and assertions.
    """
    
    status_code: int
    headers: dict[str, str]
    content: bytes
    cookies: SimpleCookie
    url: str
    request: dict[str, Any] | None = None
    
    @property
    def text(self) -> str:
        """Get response body as text."""
        return self.content.decode('utf-8')
    
    @property
    def json(self) -> Any:
        """Parse response body as JSON."""
        return json.loads(self.text)
    
    @property
    def ok(self) -> bool:
        """Check if response was successful (2xx)."""
        return 200 <= self.status_code < 300
    
    @property
    def redirect_chain(self) -> list[str]:
        """Get chain of redirect URLs."""
        return getattr(self, '_redirect_chain', [])
    
    def __repr__(self) -> str:
        return f"<Response [{self.status_code}]>"


class AsyncClient:
    """
    Async test client for FastStack applications.
    
    Example:
        async with AsyncClient() as client:
            # GET request
            response = await client.get('/api/users/')
            
            # POST request
            response = await client.post('/api/users/', json={
                'name': 'John',
                'email': 'john@example.com',
            })
            
            # Authenticated request
            client.login(user)
            response = await client.get('/api/profile/')
    """
    
    def __init__(
        self,
        base_url: str = "http://testserver",
        cookies: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        user: Any = None,
    ):
        """
        Initialize the async test client.
        
        Args:
            base_url: Base URL for requests
            cookies: Initial cookies
            headers: Default headers
            user: User to authenticate as
        """
        self.base_url = base_url.rstrip('/')
        self.cookies = cookies or {}
        self.default_headers = headers or {}
        self.user = user
        self._session: httpx.AsyncClient | None = None
    
    async def __aenter__(self) -> "AsyncClient":
        """Enter async context."""
        self._session = httpx.AsyncClient(
            base_url=self.base_url,
            cookies=self.cookies,
            headers=self.default_headers,
            follow_redirects=True,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        if self._session:
            await self._session.aclose()
            self._session = None
    
    def _get_session(self) -> httpx.AsyncClient:
        """Get or create session."""
        if self._session is None:
            self._session = httpx.AsyncClient(
                base_url=self.base_url,
                cookies=self.cookies,
                headers=self.default_headers,
                follow_redirects=True,
            )
        return self._session
    
    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        content: bytes | str | None = None,
    ) -> Response:
        """
        Make an HTTP request.
        
        Args:
            method: HTTP method
            path: Request path
            params: Query parameters
            json: JSON body
            data: Form data
            files: Files to upload
            headers: Request headers
            cookies: Request cookies
            content: Raw content
        
        Returns:
            Response object
        """
        session = self._get_session()
        
        # Build request
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)
        
        # Add auth header if user is set
        if self.user:
            # Create JWT token for user
            from faststack.auth.jwt import create_access_token
            token = create_access_token(
                data={"sub": str(self.user.id), "email": self.user.email}
            )
            request_headers["Authorization"] = f"Bearer {token}"
        
        # Merge cookies
        request_cookies = {**self.cookies}
        if cookies:
            request_cookies.update(cookies)
        
        # Make request
        response = await session.request(
            method=method,
            url=path,
            params=params,
            json=json,
            data=data,
            files=files,
            headers=request_headers,
            cookies=request_cookies,
            content=content,
        )
        
        # Update cookies from response
        self.cookies.update(dict(response.cookies))
        
        # Wrap response
        return Response(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,
            cookies=response.cookies,
            url=str(response.url),
        )
    
    async def get(self, path: str, **kwargs) -> Response:
        """Make a GET request."""
        return await self.request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs) -> Response:
        """Make a POST request."""
        return await self.request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs) -> Response:
        """Make a PUT request."""
        return await self.request("PUT", path, **kwargs)
    
    async def patch(self, path: str, **kwargs) -> Response:
        """Make a PATCH request."""
        return await self.request("PATCH", path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> Response:
        """Make a DELETE request."""
        return await self.request("DELETE", path, **kwargs)
    
    async def head(self, path: str, **kwargs) -> Response:
        """Make a HEAD request."""
        return await self.request("HEAD", path, **kwargs)
    
    async def options(self, path: str, **kwargs) -> Response:
        """Make an OPTIONS request."""
        return await self.request("OPTIONS", path, **kwargs)
    
    def login(self, user: Any) -> None:
        """
        Authenticate as a user.
        
        Args:
            user: User instance
        """
        self.user = user
    
    def logout(self) -> None:
        """Clear authentication."""
        self.user = None
        self.cookies = {}
    
    async def force_login(self, user: Any) -> None:
        """
        Force login without authentication.
        
        Similar to login() but bypasses any auth checks.
        
        Args:
            user: User instance
        """
        self.user = user
    
    def session(self) -> dict[str, Any]:
        """Get session data."""
        # Decode session cookie
        session_cookie = self.cookies.get('session_id')
        if not session_cookie:
            return {}
        
        # Decode session (simplified)
        from itsdangerous import URLSafeTimedSerializer
        from faststack.config import settings
        
        serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
        try:
            return serializer.loads(session_cookie)
        except Exception:
            return {}


class Client(AsyncClient):
    """
    Sync test client wrapper.
    
    Provides synchronous interface for simple tests.
    """
    
    def request(self, method: str, path: str, **kwargs) -> Response:
        """Make a synchronous request."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            super().request(method, path, **kwargs)
        )
    
    def get(self, path: str, **kwargs) -> Response:
        return self.request("GET", path, **kwargs)
    
    def post(self, path: str, **kwargs) -> Response:
        return self.request("POST", path, **kwargs)
    
    def put(self, path: str, **kwargs) -> Response:
        return self.request("PUT", path, **kwargs)
    
    def patch(self, path: str, **kwargs) -> Response:
        return self.request("PATCH", path, **kwargs)
    
    def delete(self, path: str, **kwargs) -> Response:
        return self.request("DELETE", path, **kwargs)
