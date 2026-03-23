"""
FastStack Middleware - Clickjacking and CORS protection.
"""

from typing import Any, Callable, List, Optional


class XFrameOptionsMiddleware:
    """
    Middleware to prevent clickjacking via X-Frame-Options header.

    This middleware adds the X-Frame-Options header to all responses
    to prevent the page from being embedded in an iframe on another site.

    Example:
        app = FastStack()
        app.add_middleware(XFrameOptionsMiddleware, value='DENY')

    Configuration:
        value: 'DENY', 'SAMEORIGIN', or 'ALLOW-FROM uri'
               Default: 'SAMEORIGIN'
    """

    def __init__(
        self,
        app: Any,
        value: str = 'SAMEORIGIN',
        exempt_urls: List[str] = None
    ):
        self.app = app
        self.value = value
        self.exempt_urls = exempt_urls or []

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # Check if URL is exempt
        path = scope.get('path', '')
        if path in self.exempt_urls:
            await self.app(scope, receive, send)
            return

        # Wrap send to add header
        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))

                # Check if header already set
                has_x_frame = any(
                    h[0].lower() == b'x-frame-options' for h in headers
                )

                if not has_x_frame:
                    headers.append((b'x-frame-options', self.value.encode()))

                message['headers'] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)


class ContentSecurityPolicyMiddleware:
    """
    Middleware to add Content-Security-Policy header.

    Example:
        app = FastStack()
        app.add_middleware(ContentSecurityPolicyMiddleware, policy="default-src 'self'")

    Configuration:
        policy: CSP policy string
        report_only: Set to True to use Content-Security-Policy-Report-Only
    """

    def __init__(
        self,
        app: Any,
        policy: str = None,
        report_only: bool = False
    ):
        self.app = app
        self.policy = policy or "default-src 'self'"
        self.report_only = report_only

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))

                header_name = (
                    'content-security-policy-report-only'
                    if self.report_only
                    else 'content-security-policy'
                )

                # Check if header already set
                has_csp = any(
                    h[0].decode().lower() == header_name for h in headers
                )

                if not has_csp:
                    headers.append((header_name.encode(), self.policy.encode()))

                message['headers'] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)


class CORSMiddleware:
    """
    Cross-Origin Resource Sharing middleware.

    Enables CORS for API endpoints and cross-origin requests.

    Example:
        app = FastStack()
        app.add_middleware(CORSMiddleware, 
            allow_origins=['https://example.com'],
            allow_methods=['GET', 'POST'],
            allow_headers=['*'],
            allow_credentials=True
        )
    """

    def __init__(
        self,
        app: Any,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        allow_origin_regex: str = None,
        expose_headers: List[str] = None,
        max_age: int = 600,
    ):
        self.app = app
        self.allow_origins = allow_origins or ['*']
        self.allow_methods = allow_methods or ['*']
        self.allow_headers = allow_headers or ['*']
        self.allow_credentials = allow_credentials
        self.allow_origin_regex = allow_origin_regex
        self.expose_headers = expose_headers or []
        self.max_age = max_age

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # Handle preflight
        if scope['method'] == 'OPTIONS':
            response = self._preflight_response(scope)
            await response(scope, receive, send)
            return

        # Handle normal request
        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))

                # Add CORS headers
                origin = self._get_origin(scope)

                if self._is_allowed_origin(origin):
                    headers.append((b'access-control-allow-origin', origin.encode()))

                    if self.allow_credentials:
                        headers.append((b'access-control-allow-credentials', b'true'))

                    if self.expose_headers:
                        headers.append((
                            b'access-control-expose-headers',
                            ', '.join(self.expose_headers).encode()
                        ))

                message['headers'] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _preflight_response(self, scope):
        """Create preflight response."""
        from starlette.responses import Response

        headers = {}

        origin = self._get_origin(scope)
        if self._is_allowed_origin(origin):
            headers['access-control-allow-origin'] = origin

            if self.allow_methods == ['*']:
                request_method = dict(scope.get('headers', [])).get(b'access-control-request-method', b'*').decode()
                headers['access-control-allow-methods'] = request_method
            else:
                headers['access-control-allow-methods'] = ', '.join(self.allow_methods)

            if self.allow_headers == ['*']:
                request_headers = dict(scope.get('headers', [])).get(b'access-control-request-headers', b'*').decode()
                headers['access-control-allow-headers'] = request_headers
            else:
                headers['access-control-allow-headers'] = ', '.join(self.allow_headers)

            if self.allow_credentials:
                headers['access-control-allow-credentials'] = 'true'

            headers['access-control-max-age'] = str(self.max_age)

        return Response(headers=headers)

    def _get_origin(self, scope) -> str:
        """Get origin from request headers."""
        headers = dict(scope.get('headers', []))
        return headers.get(b'origin', headers.get(b'host', b'')).decode()

    def _is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is allowed."""
        if '*' in self.allow_origins:
            return True

        if origin in self.allow_origins:
            return True

        if self.allow_origin_regex:
            import re
            if re.match(self.allow_origin_regex, origin):
                return True

        return False


class SecurityHeadersMiddleware:
    """
    Middleware to add various security headers.

    Adds common security headers to all responses.

    Example:
        app = FastStack()
        app.add_middleware(SecurityHeadersMiddleware)
    """

    def __init__(
        self,
        app: Any,
        content_type_nosniff: bool = True,
        xss_protection: bool = True,
        hsts: bool = False,
        hsts_max_age: int = 31536000,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        referrer_policy: str = 'strict-origin-when-cross-origin',
        permissions_policy: str = None,
    ):
        self.app = app
        self.content_type_nosniff = content_type_nosniff
        self.xss_protection = xss_protection
        self.hsts = hsts
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))
                existing = {h[0].lower() for h in headers}

                # X-Content-Type-Options
                if self.content_type_nosniff and b'x-content-type-options' not in existing:
                    headers.append((b'x-content-type-options', b'nosniff'))

                # X-XSS-Protection (deprecated but still useful for older browsers)
                if self.xss_protection and b'x-xss-protection' not in existing:
                    headers.append((b'x-xss-protection', b'1; mode=block'))

                # Strict-Transport-Security
                if self.hsts and b'strict-transport-security' not in existing:
                    hsts_value = f'max-age={self.hsts_max_age}'
                    if self.hsts_include_subdomains:
                        hsts_value += '; includeSubDomains'
                    if self.hsts_preload:
                        hsts_value += '; preload'
                    headers.append((b'strict-transport-security', hsts_value.encode()))

                # Referrer-Policy
                if self.referrer_policy and b'referrer-policy' not in existing:
                    headers.append((b'referrer-policy', self.referrer_policy.encode()))

                # Permissions-Policy (formerly Feature-Policy)
                if self.permissions_policy and b'permissions-policy' not in existing:
                    headers.append((b'permissions-policy', self.permissions_policy.encode()))

                message['headers'] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)
