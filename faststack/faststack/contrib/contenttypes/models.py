"""
ContentType model for generic relations.
"""

from typing import Any, Dict, Optional, Type, TypeVar
from dataclasses import dataclass, field
import hashlib

T = TypeVar('T')


@dataclass
class ContentType:
    """
    Represents a model type in the system.

    Each registered model has a corresponding ContentType entry
    that allows for generic relations.

    Attributes:
        id: Unique identifier
        app_label: Application/module name
        model: Model class name
    """

    id: int
    app_label: str
    model: str

    # Cache for content types
    _cache: Dict[str, 'ContentType'] = field(default_factory=dict, repr=False)
    _id_cache: Dict[int, 'ContentType'] = field(default_factory=dict, repr=False)

    def __repr__(self) -> str:
        return f"ContentType(id={self.id}, app_label='{self.app_label}', model='{self.model}')"

    def __str__(self) -> str:
        return f"{self.app_label}.{self.model}"

    @property
    def name(self) -> str:
        """Human-readable name."""
        return self.model.replace('_', ' ').title()

    @property
    def app_label(self) -> str:
        """Application label."""
        return self._app_label

    @app_label.setter
    def app_label(self, value: str):
        self._app_label = value

    def model_class(self) -> Optional[Type]:
        """
        Get the model class for this content type.

        Returns:
            The model class or None if not found
        """
        try:
            # Try to import the model
            import importlib
            module = importlib.import_module(self.app_label)
            return getattr(module, self.model, None)
        except (ImportError, AttributeError):
            return None

    def get_object_for_this_type(self, object_id: Any) -> Any:
        """
        Get an object of this type by ID.

        Args:
            object_id: The object's primary key

        Returns:
            The model instance
        """
        model = self.model_class()
        if model and hasattr(model, 'get'):
            return model.get(id=object_id)
        return None

    async def aget_object_for_this_type(self, object_id: Any) -> Any:
        """Async get an object of this type by ID."""
        model = self.model_class()
        if model and hasattr(model, 'get'):
            return await model.get(id=object_id)
        return None

    def get_all_objects_for_this_type(self, **filters) -> Any:
        """
        Get all objects of this type matching filters.

        Args:
            **filters: Filter arguments

        Returns:
            Queryset of matching objects
        """
        model = self.model_class()
        if model and hasattr(model, 'filter'):
            return model.filter(**filters)
        return []

    def natural_key(self) -> tuple:
        """Get natural key (app_label, model)."""
        return (self.app_label, self.model)

    @classmethod
    def get_by_natural_key(cls, app_label: str, model: str) -> 'ContentType':
        """Get ContentType by natural key."""
        return ContentTypeManager.get_by_natural_key(app_label, model)


class ContentTypeManager:
    """
    Manager for ContentType operations.

    Provides methods for getting and creating ContentType instances.
    """

    # In-memory cache (would be DB in production)
    _cache: Dict[str, ContentType] = {}
    _id_cache: Dict[int, ContentType] = {}
    _next_id: int = 1

    @classmethod
    def get_for_model(cls, model: Type) -> ContentType:
        """
        Get ContentType for a model class.

        Args:
            model: The model class

        Returns:
            ContentType instance
        """
        # Get app_label and model name
        app_label = model.__module__.split('.')[0]
        model_name = model.__name__.lower()

        key = f"{app_label}.{model_name}"

        if key in cls._cache:
            return cls._cache[key]

        # Create new ContentType
        ct = ContentType(
            id=cls._next_id,
            app_label=app_label,
            model=model_name
        )
        cls._next_id += 1

        # Cache it
        cls._cache[key] = ct
        cls._id_cache[ct.id] = ct

        return ct

    @classmethod
    def get_for_models(cls, *models: Type) -> Dict[Type, ContentType]:
        """
        Get ContentTypes for multiple models.

        Args:
            *models: Model classes

        Returns:
            Dictionary mapping models to ContentTypes
        """
        return {model: cls.get_for_model(model) for model in models}

    @classmethod
    def get_by_natural_key(cls, app_label: str, model: str) -> ContentType:
        """Get ContentType by natural key."""
        key = f"{app_label}.{model.lower()}"

        if key in cls._cache:
            return cls._cache[key]

        # Create if not exists
        ct = ContentType(
            id=cls._next_id,
            app_label=app_label,
            model=model.lower()
        )
        cls._next_id += 1

        cls._cache[key] = ct
        cls._id_cache[ct.id] = ct

        return ct

    @classmethod
    def get_by_id(cls, id: int) -> Optional[ContentType]:
        """Get ContentType by ID."""
        return cls._id_cache.get(id)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached ContentTypes."""
        cls._cache.clear()
        cls._id_cache.clear()

    @classmethod
    def all(cls) -> list:
        """Get all ContentTypes."""
        return list(cls._cache.values())


# Convenience function
def get_content_type(obj: Any) -> ContentType:
    """
    Get ContentType for an object or model class.

    Args:
        obj: Model instance or class

    Returns:
        ContentType instance
    """
    if isinstance(obj, ContentType):
        return obj

    model = obj.__class__ if hasattr(obj, 'id') else obj
    return ContentTypeManager.get_for_model(model)
