"""
FastStack Router Module

Provides centralized routing with automatic mounting of app routers
and prefix handling for API, admin, and web routes.
"""

from typing import Any, Callable
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse


class RouterManager:
    """
    Central router management for FastStack applications.

    Manages:
    - API routes (/api)
    - Web routes (/)
    - Admin routes (/admin)
    """

    def __init__(self):
        """Initialize router manager with separate routers for each route type."""
        self.api_router = APIRouter(prefix="/api", tags=["api"])
        self.web_router = APIRouter(tags=["web"])
        self.admin_router = APIRouter(prefix="/admin", tags=["admin"])

        # Store registered apps
        self._registered_apps: dict[str, dict[str, Any]] = {}

    def register_app(
        self,
        app_name: str,
        router: APIRouter | None = None,
        admin_router: APIRouter | None = None,
        api_router: APIRouter | None = None,
        models: list[Any] | None = None,
    ) -> None:
        """
        Register an app's routers.

        Args:
            app_name: Name of the app
            router: Web routes router
            admin_router: Admin panel routes
            api_router: API routes router
            models: List of models for admin registration
        """
        self._registered_apps[app_name] = {
            "router": router,
            "admin_router": admin_router,
            "api_router": api_router,
            "models": models or [],
        }

        # Mount routers
        if router:
            self.web_router.include_router(router, prefix=f"/{app_name}")

        if admin_router:
            self.admin_router.include_router(admin_router, prefix=f"/{app_name}")

        if api_router:
            self.api_router.include_router(api_router, prefix=f"/{app_name}")

    def get_registered_apps(self) -> dict[str, dict[str, Any]]:
        """Get all registered apps."""
        return self._registered_apps

    def mount_to_app(self, app: FastAPI) -> None:
        """
        Mount all routers to a FastAPI application.

        Args:
            app: FastAPI application instance
        """
        app.include_router(self.api_router)
        app.include_router(self.web_router)
        app.include_router(self.admin_router)


# Global router manager instance
router_manager = RouterManager()


def get_api_router() -> APIRouter:
    """Get the main API router."""
    return router_manager.api_router


def get_web_router() -> APIRouter:
    """Get the main web router."""
    return router_manager.web_router


def get_admin_router() -> APIRouter:
    """Get the main admin router."""
    return router_manager.admin_router


def api_route(
    path: str = "",
    *,
    methods: list[str] | None = None,
    **kwargs,
) -> Callable:
    """
    Decorator to register an API route.

    Args:
        path: URL path (will be prefixed with /api)
        methods: HTTP methods (default: ["GET"])
        **kwargs: Additional route options

    Example:
        @api_route("/users", methods=["GET"])
        async def get_users():
            return {"users": []}
    """
    if methods is None:
        methods = ["GET"]

    def decorator(func: Callable) -> Callable:
        router_manager.api_router.add_api_route(
            path, func, methods=methods, **kwargs
        )
        return func

    return decorator


def web_route(
    path: str = "",
    *,
    methods: list[str] | None = None,
    **kwargs,
) -> Callable:
    """
    Decorator to register a web route.

    Args:
        path: URL path
        methods: HTTP methods (default: ["GET"])
        **kwargs: Additional route options

    Example:
        @web_route("/", methods=["GET"])
        async def home(request: Request):
            return templates.TemplateResponse("home.html", {"request": request})
    """
    if methods is None:
        methods = ["GET"]

    def decorator(func: Callable) -> Callable:
        router_manager.web_router.add_api_route(
            path, func, methods=methods, **kwargs
        )
        return func

    return decorator


def admin_route(
    path: str = "",
    *,
    methods: list[str] | None = None,
    **kwargs,
) -> Callable:
    """
    Decorator to register an admin route.

    Args:
        path: URL path (will be prefixed with /admin)
        methods: HTTP methods (default: ["GET"])
        **kwargs: Additional route options

    Example:
        @admin_route("/dashboard", methods=["GET"])
        async def admin_dashboard(request: Request):
            return templates.TemplateResponse("admin/dashboard.html", {"request": request})
    """
    if methods is None:
        methods = ["GET"]

    def decorator(func: Callable) -> Callable:
        router_manager.admin_router.add_api_route(
            path, func, methods=methods, **kwargs
        )
        return func

    return decorator
