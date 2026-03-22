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

    templates.env.filters["datetime"] = datetime_format
    templates.env.filters["date"] = date_format
    templates.env.filters["time"] = time_format
    templates.env.filters["truncate"] = truncate


def _add_template_globals(templates: Jinja2Templates) -> None:
    """Add custom Jinja2 globals."""
    templates.env.globals["settings"] = settings
    templates.env.globals["debug"] = settings.DEBUG


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
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

    return app


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
