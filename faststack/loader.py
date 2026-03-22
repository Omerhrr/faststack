"""
FastStack App Loader Module

Provides automatic discovery and loading of app modules.
Scans the apps directory and dynamically imports routes, models, and admin configurations.
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from sqlmodel import SQLModel

from faststack.config import settings
from faststack.router import router_manager


class AppLoader:
    """
    Automatic app discovery and loading system.

    Scans the apps directory for valid FastStack apps and loads their:
    - routes.py (web routes)
    - models.py (database models)
    - admin.py (admin configuration)
    - api.py (API routes)
    """

    def __init__(self, apps_dir: Path | str | None = None):
        """
        Initialize the app loader.

        Args:
            apps_dir: Directory containing app modules (default: from settings)
        """
        self.apps_dir = Path(apps_dir) if apps_dir else settings.apps_dir
        self._loaded_apps: dict[str, dict[str, Any]] = {}
        self._models: list[type[SQLModel]] = []

    def discover_apps(self) -> list[str]:
        """
        Discover all valid apps in the apps directory.

        Returns:
            List of app names
        """
        if not self.apps_dir.exists():
            return []

        apps = []
        for item in self.apps_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                # Check if it has __init__.py or routes.py/models.py
                init_file = item / "__init__.py"
                routes_file = item / "routes.py"
                models_file = item / "models.py"

                if init_file.exists() or routes_file.exists() or models_file.exists():
                    apps.append(item.name)

        return sorted(apps)

    def load_app(self, app_name: str) -> dict[str, Any] | None:
        """
        Load a single app's modules.

        Args:
            app_name: Name of the app to load

        Returns:
            Dictionary with loaded components or None if loading failed
        """
        app_path = self.apps_dir / app_name
        if not app_path.exists():
            return None

        loaded = {
            "name": app_name,
            "path": app_path,
            "router": None,
            "api_router": None,
            "admin_router": None,
            "models": [],
            "services": None,
        }

        # Add app to Python path if not already there
        if str(self.apps_dir) not in sys.path:
            sys.path.insert(0, str(self.apps_dir))

        # Load models first (needed for relationships)
        models = self._load_models(app_name, app_path)
        loaded["models"] = models
        self._models.extend(models)

        # Load routes
        router = self._load_routes(app_name, app_path)
        loaded["router"] = router

        # Load API routes
        api_router = self._load_api(app_name, app_path)
        loaded["api_router"] = api_router

        # Load admin
        admin_router = self._load_admin(app_name, app_path)
        loaded["admin_router"] = admin_router

        # Load services
        services = self._load_services(app_name, app_path)
        loaded["services"] = services

        self._loaded_apps[app_name] = loaded
        return loaded

    def _load_models(
        self, app_name: str, app_path: Path
    ) -> list[type[SQLModel]]:
        """Load models from models.py."""
        models = []
        models_file = app_path / "models.py"

        if models_file.exists():
            try:
                # Import the models module
                spec = importlib.util.spec_from_file_location(
                    f"apps.{app_name}.models", models_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[f"apps.{app_name}.models"] = module
                    spec.loader.exec_module(module)

                    # Find all SQLModel subclasses
                    for name in dir(module):
                        obj = getattr(module, name)
                        if (
                            isinstance(obj, type)
                            and issubclass(obj, SQLModel)
                            and obj is not SQLModel
                        ):
                            models.append(obj)
            except Exception as e:
                if settings.DEBUG:
                    print(f"Warning: Failed to load models from {app_name}: {e}")

        return models

    def _load_routes(self, app_name: str, app_path: Path) -> APIRouter | None:
        """Load web routes from routes.py."""
        routes_file = app_path / "routes.py"

        if routes_file.exists():
            try:
                spec = importlib.util.spec_from_file_location(
                    f"apps.{app_name}.routes", routes_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[f"apps.{app_name}.routes"] = module
                    spec.loader.exec_module(module)

                    # Look for router attribute
                    if hasattr(module, "router"):
                        return module.router
                    elif hasattr(module, "app"):
                        return module.app

            except Exception as e:
                if settings.DEBUG:
                    print(f"Warning: Failed to load routes from {app_name}: {e}")

        return None

    def _load_api(self, app_name: str, app_path: Path) -> APIRouter | None:
        """Load API routes from api.py."""
        api_file = app_path / "api.py"

        if api_file.exists():
            try:
                spec = importlib.util.spec_from_file_location(
                    f"apps.{app_name}.api", api_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[f"apps.{app_name}.api"] = module
                    spec.loader.exec_module(module)

                    if hasattr(module, "router"):
                        return module.router

            except Exception as e:
                if settings.DEBUG:
                    print(f"Warning: Failed to load API from {app_name}: {e}")

        return None

    def _load_admin(self, app_name: str, app_path: Path) -> APIRouter | None:
        """Load admin configuration from admin.py."""
        admin_file = app_path / "admin.py"

        if admin_file.exists():
            try:
                spec = importlib.util.spec_from_file_location(
                    f"apps.{app_name}.admin", admin_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[f"apps.{app_name}.admin"] = module
                    spec.loader.exec_module(module)

                    if hasattr(module, "router"):
                        return module.router

            except Exception as e:
                if settings.DEBUG:
                    print(f"Warning: Failed to load admin from {app_name}: {e}")

        return None

    def _load_services(self, app_name: str, app_path: Path) -> Any | None:
        """Load services from services.py."""
        services_file = app_path / "services.py"

        if services_file.exists():
            try:
                spec = importlib.util.spec_from_file_location(
                    f"apps.{app_name}.services", services_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[f"apps.{app_name}.services"] = module
                    spec.loader.exec_module(module)
                    return module

            except Exception as e:
                if settings.DEBUG:
                    print(f"Warning: Failed to load services from {app_name}: {e}")

        return None

    def load_all_apps(self) -> dict[str, dict[str, Any]]:
        """
        Load all discovered apps.

        Returns:
            Dictionary of loaded apps with their components
        """
        for app_name in self.discover_apps():
            self.load_app(app_name)

        return self._loaded_apps

    def register_all_routers(self) -> None:
        """Register all loaded app routers with the router manager."""
        for app_name, app_data in self._loaded_apps.items():
            router_manager.register_app(
                app_name=app_name,
                router=app_data.get("router"),
                admin_router=app_data.get("admin_router"),
                api_router=app_data.get("api_router"),
                models=app_data.get("models", []),
            )

    def get_all_models(self) -> list[type[SQLModel]]:
        """Get all loaded models from all apps."""
        return self._models

    def get_loaded_apps(self) -> dict[str, dict[str, Any]]:
        """Get all loaded apps."""
        return self._loaded_apps


# Global loader instance
app_loader = AppLoader()


def load_apps() -> dict[str, dict[str, Any]]:
    """
    Convenience function to load all apps.

    Returns:
        Dictionary of loaded apps
    """
    return app_loader.load_all_apps()


def get_models() -> list[type[SQLModel]]:
    """
    Convenience function to get all loaded models.

    Returns:
        List of SQLModel classes
    """
    return app_loader.get_all_models()
