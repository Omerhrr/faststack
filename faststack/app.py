"""
FastStack Application Module

Provides the main FastAPI application factory and initialization logic.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from faststack.config import settings
from faststack.database import init_db
from faststack.loader import app_loader
from faststack.router import router_manager


# Global templates instance
_templates: Jinja2Templates | None = None


def get_templates() -> Jinja2Templates:
    """
    Get the Jinja2 templates instance.

    Returns:
        Jinja2Templates: Configured templates instance
    """
    global _templates

    if _templates is None:
        template_dirs = [settings.templates_dir]

        # Add framework's built-in templates
        framework_templates = Path(__file__).parent / "templates"
        if framework_templates.exists():
            template_dirs.append(framework_templates)

        _templates = Jinja2Templates(
            directory=template_dirs,
            auto_reload=settings.TEMPLATES_AUTO_RELOAD,
        )

        # Add custom filters and globals
        _add_template_globals(_templates)
        _add_template_filters(_templates)

    return _templates


def _add_template_filters(templates: Jinja2Templates) -> None:
    """Add custom Jinja2 filters."""

    def datetime_format(value, format_string="%Y-%m-%d %H:%M"):
        """Format datetime object."""
        if value is None:
            return ""
        return value.strftime(format_string)

    def date_format(value, format_string="%Y-%m-%d"):
        """Format date object."""
        if value is None:
            return ""
        return value.strftime(format_string)

    def time_format(value, format_string="%H:%M"):
        """Format time object."""
        if value is None:
            return ""
        return value.strftime(format_string)

    def truncate(value, length=100, end="..."):
        """Truncate string to specified length."""
        if value is None:
            return ""
        if len(value) <= length:
            return value
        return value[:length] + end

    def safe_markdown(value):
        """Render markdown safely (requires markdown package)."""
        if value is None:
            return ""
        try:
            import markdown
            return markdown.markdown(value, extensions=['extra', 'codehilite'])
        except ImportError:
            return value

    def json_encode(value):
        """Convert to JSON string."""
        import json
        return json.dumps(value)

    templates.env.filters["datetime"] = datetime_format
    templates.env.filters["date"] = date_format
    templates.env.filters["time"] = time_format
    templates.env.filters["truncate"] = truncate
    templates.env.filters["markdown"] = safe_markdown
    templates.env.filters["tojson"] = json_encode


def _add_template_globals(templates: Jinja2Templates) -> None:
    """Add custom Jinja2 globals."""
    from faststack.middleware.csrf import generate_csrf_token

    templates.env.globals["settings"] = settings
    templates.env.globals["debug"] = settings.DEBUG

    def csrf_token():
        """Generate a CSRF token for forms."""
        return generate_csrf_token()

    templates.env.globals["csrf_token"] = csrf_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    # Create uploads directory if needed
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.exists():
        upload_dir.mkdir(parents=True, exist_ok=True)

    # Load all apps
    app_loader.load_all_apps()

    # Register all routers
    app_loader.register_all_routers()

    # Mount routers to app
    router_manager.mount_to_app(app)

    # Initialize database
    init_db()

    # Store loader reference in app state
    app.state.loader = app_loader
    app.state.templates = get_templates()

    yield

    # Shutdown
    # Add cleanup logic here if needed
    pass


def create_app(
    title: str | None = None,
    description: str | None = None,
    version: str = "0.1.0",
    enable_session: bool = True,
    enable_csrf: bool = True,
    enable_rate_limit: bool = True,
    enable_security_headers: bool = True,
    **kwargs: Any,
) -> FastAPI:
    """
    Create and configure a FastAPI application.

    This is the main factory function for creating FastStack applications.
    It sets up middleware, routing, templates, and static files.

    Args:
        title: Application title (default: from settings)
        description: Application description
        version: Application version
        enable_session: Enable session middleware
        enable_csrf: Enable CSRF protection
        enable_rate_limit: Enable rate limiting
        enable_security_headers: Enable security headers
        **kwargs: Additional FastAPI configuration options

    Returns:
        FastAPI: Configured FastAPI application

    Example:
        app = create_app()
        # or
        app = create_app(title="My App", version="1.0.0")
    """
    app = FastAPI(
        title=title or settings.APP_NAME,
        description=description or "FastStack Application",
        version=version,
        debug=settings.DEBUG,
        lifespan=lifespan,
        **kwargs,
    )

    # Add Session Middleware (must be first for proper session handling)
    if enable_session:
        app.add_middleware(
            SessionMiddleware,
            secret_key=settings.SECRET_KEY,
            session_cookie=settings.SESSION_COOKIE_NAME,
            max_age=settings.SESSION_MAX_AGE,
            same_site=settings.SESSION_COOKIE_SAMESITE,
            https_only=settings.SESSION_COOKIE_SECURE,
        )

    # Add Security Headers Middleware
    if enable_security_headers and settings.SECURITY_HEADERS_ENABLED:
        from faststack.middleware.security import SecurityHeadersMiddleware
        app.add_middleware(SecurityHeadersMiddleware, enable_hsts=settings.HSTS_ENABLED)

    # Add Rate Limiting Middleware
    if enable_rate_limit and settings.RATE_LIMIT_ENABLED:
        from faststack.middleware.ratelimit import RateLimitMiddleware
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
            requests_per_hour=settings.RATE_LIMIT_REQUESTS_PER_HOUR,
            block_duration=settings.RATE_LIMIT_BLOCK_DURATION,
        )

    # Add CSRF Middleware
    if enable_csrf and settings.CSRF_ENABLED:
        from faststack.middleware.csrf import CSRFMiddleware
        app.add_middleware(
            CSRFMiddleware,
            secret_key=settings.SECRET_KEY,
            token_name=settings.CSRF_TOKEN_NAME,
            header_name=settings.CSRF_HEADER_NAME,
            cookie_name=settings.CSRF_COOKIE_NAME,
            expiry=settings.CSRF_EXPIRY,
        )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Mount static files
    static_dir = settings.static_dir
    if static_dir.exists():
        app.mount(
            settings.STATIC_URL,
            StaticFiles(directory=str(static_dir)),
            name="static",
        )

    # Add home route
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def home(request: Request):
        """Render home page."""
        templates = get_templates()
        return templates.TemplateResponse(
            "pages/home.html",
            {"request": request, "title": settings.APP_NAME},
        )

    # Add health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "app": settings.APP_NAME}

    # Add error handlers
    _add_error_handlers(app)

    return app


def _add_error_handlers(app: FastAPI) -> None:
    """Add custom error handlers for common HTTP errors."""

    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with custom error pages."""
        templates = get_templates()

        # Check if it's an HTMX request
        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content=f'<div class="alert alert-error">{exc.detail}</div>',
                status_code=exc.status_code,
            )

        # Return custom error page based on status code
        if exc.status_code == 404:
            return templates.TemplateResponse(
                "errors/404.html",
                {"request": request, "error": exc},
                status_code=404,
            )
        elif exc.status_code == 403:
            return templates.TemplateResponse(
                "errors/403.html",
                {"request": request, "error": exc},
                status_code=403,
            )
        elif exc.status_code >= 500:
            return templates.TemplateResponse(
                "errors/500.html",
                {"request": request, "error": exc},
                status_code=exc.status_code,
            )

        # Default error response
        return templates.TemplateResponse(
            "errors/error.html",
            {"request": request, "error": exc},
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        templates = get_templates()

        if request.headers.get("HX-Request"):
            errors = "; ".join([str(e) for e in exc.errors()])
            return HTMLResponse(
                content=f'<div class="alert alert-error">Validation error: {errors}</div>',
                status_code=422,
            )

        return templates.TemplateResponse(
            "errors/400.html",
            {"request": request, "errors": exc.errors()},
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        templates = get_templates()

        if settings.DEBUG:
            # Show error details in debug mode
            import traceback
            tb = traceback.format_exc()
            return templates.TemplateResponse(
                "errors/debug.html",
                {"request": request, "error": exc, "traceback": tb},
                status_code=500,
            )

        return templates.TemplateResponse(
            "errors/500.html",
            {"request": request, "error": exc},
            status_code=500,
        )


# Global app instance (lazy-loaded)
_app: FastAPI | None = None


def get_app() -> FastAPI:
    """
    Get or create the global FastAPI application instance.

    This function provides a singleton pattern for the app instance.

    Returns:
        FastAPI: The global FastAPI application
    """
    global _app

    if _app is None:
        _app = create_app()

    return _app
