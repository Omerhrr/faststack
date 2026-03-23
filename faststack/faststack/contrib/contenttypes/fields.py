"""
Generic relation fields for ContentTypes.
"""

from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING
from dataclasses import dataclass, field
import asyncio

if TYPE_CHECKING:
    from .models import ContentType


@dataclass
class GenericForeignKey:
    """
    A field that can point to any model.

    Requires two concrete fields: one for the ContentType
    and one for the object ID.

    Example:
        class Comment(Model):
            content_type_id = IntegerField()
            object_id = IntegerField()
            content_object = GenericForeignKey('content_type_id', 'object_id')

        # Set the generic relation
        comment.content_object = some_post
        await comment.save()

        # Get the related object
        obj = comment.content_object
    """

    ct_field: str = 'content_type_id'
    fk_field: str = 'object_id'

    # Cache for the related object
    _cache: Dict[int, Any] = field(default_factory=dict, repr=False)

    def __init__(self, ct_field: str = 'content_type_id', fk_field: str = 'object_id'):
        """
        Initialize GenericForeignKey.

        Args:
            ct_field: Name of the ContentType FK field
            fk_field: Name of the object ID field
        """
        self.ct_field = ct_field
        self.fk_field = fk_field
        self._cache = {}

    def __get__(self, instance: Any, owner: Type = None) -> Any:
        """Get the related object."""
        if instance is None:
            return self

        # Get content type and object ID
        ct_id = getattr(instance, self.ct_field, None)
        obj_id = getattr(instance, self.fk_field, None)

        if ct_id is None or obj_id is None:
            return None

        # Check cache
        cache_key = (ct_id, obj_id)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Get the content type
        from .models import ContentTypeManager
        ct = ContentTypeManager.get_by_id(ct_id)

        if ct is None:
            return None

        # Get the related object
        model = ct.model_class()
        if model and hasattr(model, 'get'):
            obj = model.get(id=obj_id)
            # Try async get
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Return a coroutine that needs to be awaited
                    return model.get(id=obj_id)
                obj = loop.run_until_complete(model.get(id=obj_id))
            except RuntimeError:
                # Return sync
                try:
                    obj = model.get(id=obj_id)
                except:
                    obj = None

            self._cache[cache_key] = obj
            return obj

        return None

    def __set__(self, instance: Any, value: Any) -> None:
        """Set the related object."""
        if value is None:
            setattr(instance, self.ct_field, None)
            setattr(instance, self.fk_field, None)
            return

        # Get content type for the object
        from .models import ContentTypeManager
        ct = ContentTypeManager.get_for_model(value.__class__)

        # Set the fields
        setattr(instance, self.ct_field, ct.id)
        setattr(instance, self.fk_field, value.id)

        # Cache the object
        self._cache[(ct.id, value.id)] = value


@dataclass
class GenericRelation:
    """
    Reverse generic relation.

    Add this to a model to get all related objects from a GenericForeignKey.

    Example:
        class Post(Model):
            title = CharField()
            comments = GenericRelation('Comment', related_query_name='posts')

        # Get all comments for a post
        post = await Post.get(id=1)
        comments = await post.comments.all()
    """

    model: Type
    content_type_field: str = 'content_type_id'
    object_id_field: str = 'object_id'
    related_query_name: str = ''
    related_name: str = ''

    def __init__(
        self,
        model: Type,
        content_type_field: str = 'content_type_id',
        object_id_field: str = 'object_id',
        related_query_name: str = '',
        related_name: str = ''
    ):
        """
        Initialize GenericRelation.

        Args:
            model: The related model class
            content_type_field: Name of the ContentType FK on related model
            object_id_field: Name of the object ID on related model
            related_query_name: Name for reverse queries
            related_name: Name for reverse accessor
        """
        self.model = model
        self.content_type_field = content_type_field
        self.object_id_field = object_id_field
        self.related_query_name = related_query_name
        self.related_name = related_name

    def __get__(self, instance: Any, owner: Type = None) -> 'GenericRelatedObjectManager':
        """Get the related objects manager."""
        if instance is None:
            return self

        return GenericRelatedObjectManager(
            instance=instance,
            model=self.model,
            ct_field=self.content_type_field,
            fk_field=self.object_id_field
        )


class GenericRelatedObjectManager:
    """
    Manager for generic related objects.
    """

    def __init__(
        self,
        instance: Any,
        model: Type,
        ct_field: str,
        fk_field: str
    ):
        self.instance = instance
        self.model = model
        self.ct_field = ct_field
        self.fk_field = fk_field

    async def all(self) -> List[Any]:
        """Get all related objects."""
        from .models import ContentTypeManager

        ct = ContentTypeManager.get_for_model(self.instance.__class__)

        if hasattr(self.model, 'filter'):
            return await self.model.filter(**{
                self.ct_field: ct.id,
                self.fk_field: self.instance.id
            })

        return []

    async def count(self) -> int:
        """Count related objects."""
        from .models import ContentTypeManager

        ct = ContentTypeManager.get_for_model(self.instance.__class__)

        if hasattr(self.model, 'count'):
            return await self.model.count(**{
                self.ct_field: ct.id,
                self.fk_field: self.instance.id
            })

        return 0

    async def add(self, *objs: Any) -> None:
        """Add objects to the relation."""
        for obj in objs:
            setattr(obj, self.ct_field, ContentTypeManager.get_for_model(self.instance.__class__).id)
            setattr(obj, self.fk_field, self.instance.id)
            if hasattr(obj, 'save'):
                await obj.save()

    async def remove(self, *objs: Any) -> None:
        """Remove objects from the relation."""
        for obj in objs:
            setattr(obj, self.ct_field, None)
            setattr(obj, self.fk_field, None)
            if hasattr(obj, 'save'):
                await obj.save()

    async def clear(self) -> None:
        """Clear all related objects."""
        related = await self.all()
        for obj in related:
            setattr(obj, self.ct_field, None)
            setattr(obj, self.fk_field, None)
            if hasattr(obj, 'save'):
                await obj.save()

    async def create(self, **kwargs) -> Any:
        """Create a new related object."""
        from .models import ContentTypeManager

        ct = ContentTypeManager.get_for_model(self.instance.__class__)

        kwargs[self.ct_field] = ct.id
        kwargs[self.fk_field] = self.instance.id

        if hasattr(self.model, 'create'):
            return await self.model.create(**kwargs)

        return None
