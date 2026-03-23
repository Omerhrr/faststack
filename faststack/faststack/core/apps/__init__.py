"""
FastStack Apps Registry - Installed apps system.

Example:
    from faststack.core.apps import apps

    # Get app config
    app_config = apps.get_app_config('blog')

    # Get model
    Post = apps.get_model('blog', 'Post')

    # Get all models
    models = apps.get_models()

    # Check if app is installed
    apps.is_installed('blog')
"""

from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
import importlib
import inspect


@dataclass
class AppConfig:
    """
    Configuration for an installed app.

    Attributes:
        name: App name (module path)
        label: Short label for the app
        verbose_name: Human-readable name
        path: Filesystem path to app
        models_module: Module containing models

    Example:
        class BlogConfig(AppConfig):
            name = 'myapp.blog'
            label = 'blog'
            verbose_name = 'Blog'
    """

    name: str
    label: str = ''
    verbose_name: str = ''
    path: str = ''
    models_module: Any = None

    # Internal state
    _models: Dict[str, Type] = field(default_factory=dict, repr=False)
    _ready: bool = field(default=False, repr=False)

    def __post_init__(self):
        if not self.label:
            self.label = self.name.split('.')[-1]

        if not self.verbose_name:
            self.verbose_name = self.label.replace('_', ' ').title()

    def __repr__(self) -> str:
        return f"<AppConfig: {self.label}>"

    @classmethod
    def create(cls, app_name: str) -> 'AppConfig':
        """
        Create AppConfig from app name.

        Args:
            app_name: Module path to app

        Returns:
            AppConfig instance
        """
        # Try to import app
        try:
            module = importlib.import_module(app_name)
        except ImportError:
            return cls(name=app_name)

        # Look for apps.py
        try:
            apps_module = importlib.import_module(f'{app_name}.apps')
            for attr_name in dir(apps_module):
                attr = getattr(apps_module, attr_name)
                if (inspect.isclass(attr) and
                    issubclass(attr, AppConfig) and
                    attr is not AppConfig):
                    return attr(name=app_name)
        except ImportError:
            pass

        # Create default config
        return cls(name=app_name)

    def get_models(self) -> List[Type]:
        """Get all models in this app."""
        return list(self._models.values())

    def get_model(self, model_name: str) -> Optional[Type]:
        """Get model by name."""
        return self._models.get(model_name.lower())

    def register_model(self, model: Type) -> None:
        """Register a model with this app."""
        model_name = model.__name__.lower()
        self._models[model_name] = model

    def ready(self) -> None:
        """
        Called when app is ready.

        Override this method to perform initialization.
        """
        if self._ready:
            return

        # Import models
        try:
            self.models_module = importlib.import_module(f'{self.name}.models')
            self._discover_models()
        except ImportError:
            pass

        self._ready = True

    def _discover_models(self) -> None:
        """Discover and register models from models module."""
        if self.models_module is None:
            return

        for attr_name in dir(self.models_module):
            attr = getattr(self.models_module, attr_name)

            # Check if it's a model class
            if inspect.isclass(attr) and hasattr(attr, '__tablename__'):
                self.register_model(attr)


class Apps:
    """
    Registry of installed applications.

    Example:
        from faststack.core.apps import apps

        # Get app config
        blog_config = apps.get_app_config('blog')

        # Get model
        Post = apps.get_model('blog', 'Post')

        # Get all models
        all_models = apps.get_models()
    """

    def __init__(self):
        self._app_configs: Dict[str, AppConfig] = {}
        self._app_labels: Dict[str, str] = {}  # label -> name
        self._models: Dict[str, Type] = {}
        self._ready: bool = False

    def __repr__(self) -> str:
        return f"<Apps: {len(self._app_configs)} apps>"

    def populate(self, installed_apps: List[str]) -> None:
        """
        Populate registry with installed apps.

        Args:
            installed_apps: List of app module paths
        """
        for app_name in installed_apps:
            if app_name in self._app_configs:
                continue

            config = AppConfig.create(app_name)
            self._app_configs[app_name] = config
            self._app_labels[config.label] = app_name

        self._ready = True

    def ready(self) -> None:
        """Call ready() on all app configs."""
        for config in self._app_configs.values():
            config.ready()

    def get_app_configs(self) -> List[AppConfig]:
        """Get all app configs."""
        return list(self._app_configs.values())

    def get_app_config(self, app_label: str) -> AppConfig:
        """
        Get app config by label.

        Args:
            app_label: App label (e.g., 'blog')

        Returns:
            AppConfig instance

        Raises:
            LookupError: If app not found
        """
        # Try by label first
        if app_label in self._app_labels:
            return self._app_configs[self._app_labels[app_label]]

        # Try by name
        if app_label in self._app_configs:
            return self._app_configs[app_label]

        raise LookupError(f"No installed app with label '{app_label}'")

    def is_installed(self, app_name: str) -> bool:
        """
        Check if an app is installed.

        Args:
            app_name: App name or label

        Returns:
            True if installed
        """
        return app_name in self._app_configs or app_label in self._app_labels

    def get_model(self, app_label: str, model_name: str) -> Type:
        """
        Get a model by app label and model name.

        Args:
            app_label: App label (e.g., 'blog')
            model_name: Model name (e.g., 'Post')

        Returns:
            Model class

        Raises:
            LookupError: If model not found
        """
        app_config = self.get_app_config(app_label)
        model = app_config.get_model(model_name)

        if model is None:
            raise LookupError(f"Model '{model_name}' not found in app '{app_label}'")

        return model

    def get_models(self) -> List[Type]:
        """Get all registered models."""
        models = []
        for config in self._app_configs.values():
            models.extend(config.get_models())
        return models

    def get_models_for_app(self, app_label: str) -> List[Type]:
        """Get models for a specific app."""
        return self.get_app_config(app_label).get_models()

    def register_model(self, app_label: str, model: Type) -> None:
        """
        Register a model with an app.

        Args:
            app_label: App label
            model: Model class
        """
        app_config = self.get_app_config(app_label)
        app_config.register_model(model)

        # Also register globally
        model_key = f"{app_label}.{model.__name__.lower()}"
        self._models[model_key] = model


# Global apps registry
apps = Apps()
