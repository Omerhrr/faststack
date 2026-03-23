"""
ContentTypes utility functions.
"""

from typing import Any, Optional, Type, Union
from .models import ContentType, ContentTypeManager


def get_content_type(obj: Union[Any, Type], for_model: bool = False) -> ContentType:
    """
    Get ContentType for an object or model class.

    Args:
        obj: Model instance, model class, or ContentType
        for_model: If True, always return for the model class

    Returns:
        ContentType instance
    """
    if isinstance(obj, ContentType):
        return obj

    model = obj if for_model or not hasattr(obj, 'id') else obj.__class__
    return ContentTypeManager.get_for_model(model)


def get_object_for_content_type(
    content_type: Union[ContentType, int, str],
    object_id: Any,
    using: str = None
) -> Optional[Any]:
    """
    Get an object by ContentType and ID.

    Args:
        content_type: ContentType instance, ID, or "app_label.model" string
        object_id: The object's primary key
        using: Database alias (not used yet)

    Returns:
        The model instance or None
    """
    # Resolve content_type
    if isinstance(content_type, int):
        ct = ContentTypeManager.get_by_id(content_type)
    elif isinstance(content_type, str):
        app_label, model = content_type.split('.')
        ct = ContentTypeManager.get_by_natural_key(app_label, model)
    else:
        ct = content_type

    if ct is None:
        return None

    return ct.get_object_for_this_type(object_id)


async def aget_object_for_content_type(
    content_type: Union[ContentType, int, str],
    object_id: Any,
    using: str = None
) -> Optional[Any]:
    """
    Async get an object by ContentType and ID.

    Args:
        content_type: ContentType instance, ID, or "app_label.model" string
        object_id: The object's primary key
        using: Database alias (not used yet)

    Returns:
        The model instance or None
    """
    # Resolve content_type
    if isinstance(content_type, int):
        ct = ContentTypeManager.get_by_id(content_type)
    elif isinstance(content_type, str):
        app_label, model = content_type.split('.')
        ct = ContentTypeManager.get_by_natural_key(app_label, model)
    else:
        ct = content_type

    if ct is None:
        return None

    return await ct.aget_object_for_this_type(object_id)


class ContentTypeQuerySet:
    """
    QuerySet mixin for filtering by ContentType.
    """

    def filter_by_content_type(self, model: Type) -> Any:
        """
        Filter by model's ContentType.

        Args:
            model: The model class to filter by

        Returns:
            Filtered queryset
        """
        ct = ContentTypeManager.get_for_model(model)
        return self.filter(content_type_id=ct.id)

    def filter_by_object(self, obj: Any) -> Any:
        """
        Filter by object's ContentType and ID.

        Args:
            obj: The object to filter by

        Returns:
            Filtered queryset
        """
        ct = ContentTypeManager.get_for_model(obj.__class__)
        return self.filter(content_type_id=ct.id, object_id=obj.id)


def contribute_to_class(cls: Type, name: str) -> None:
    """
    Add ContentType methods to a model class.

    This is called automatically when the ContentTypes framework is enabled.

    Args:
        cls: The model class
        name: The field/accessor name
    """
    # Add get_content_type method
    def get_content_type(self):
        return ContentTypeManager.get_for_model(self.__class__)

    cls.get_content_type = get_content_type
