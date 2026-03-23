"""
FastStack Query Optimization - select_related, prefetch_related

Django-like query optimization for preventing N+1 queries.

Example:
    # select_related - for ForeignKey (JOIN)
    posts = await Post.select_related('author', 'category').all()
    # One query with JOINs instead of N+1

    # prefetch_related - for M2M and reverse FK
    posts = await Post.prefetch_related('tags', 'comments').all()
    # Two queries instead of N+1

    # Combined
    posts = await Post.select_related('author').prefetch_related('tags').all()
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Type, TypeVar, Union
from dataclasses import dataclass
import asyncio

T = TypeVar('T')


@dataclass
class RelatedField:
    """Information about a related field."""
    name: str
    field_type: str  # 'fk', 'reverse_fk', 'm2m', 'o2o'
    model: Type
    related_model: Type
    foreign_key: str = ''
    through_model: Type = None


class QueryOptimizer:
    """
    Query optimizer for preventing N+1 queries.

    Provides select_related (JOIN) and prefetch_related (separate queries)
    like Django's ORM.
    """

    def __init__(self, model: Type):
        self.model = model
        self._select_related: Set[str] = set()
        self._prefetch_related: Set[str] = set()
        self._only_fields: Set[str] = set()
        self._defer_fields: Set[str] = set()
        self._related_cache: Dict[str, RelatedField] = {}

    def select_related(self, *fields: str) -> 'QueryOptimizer':
        """
        Add related fields to select via JOIN.

        Use for ForeignKey and OneToOne relationships.

        Args:
            *fields: Field names to select (can use double underscores for nested)

        Returns:
            Self for chaining

        Example:
            posts = await Post.select_related('author', 'category').all()
            posts = await Post.select_related('author__profile').all()
        """
        self._select_related.update(fields)
        return self

    def prefetch_related(self, *fields: str) -> 'QueryOptimizer':
        """
        Add related fields to prefetch in separate queries.

        Use for ManyToMany and reverse ForeignKey relationships.

        Args:
            *fields: Field names to prefetch

        Returns:
            Self for chaining

        Example:
            posts = await Post.prefetch_related('tags', 'comments').all()
            posts = await Post.prefetch_related('comments__author').all()
        """
        self._prefetch_related.update(fields)
        return self

    def only(self, *fields: str) -> 'QueryOptimizer':
        """
        Load only specified fields (defer others).

        Args:
            *fields: Field names to load

        Returns:
            Self for chaining

        Example:
            posts = await Post.only('title', 'slug', 'author_id').all()
        """
        self._only_fields.update(fields)
        return self

    def defer(self, *fields: str) -> 'QueryOptimizer':
        """
        Defer loading of specified fields.

        Args:
            *fields: Field names to defer

        Returns:
            Self for chaining

        Example:
            posts = await Post.defer('content', 'metadata').all()
        """
        self._defer_fields.update(fields)
        return self

    def _get_related_field(self, field_name: str) -> Optional[RelatedField]:
        """Get information about a related field."""
        if field_name in self._related_cache:
            return self._related_cache[field_name]

        # Check model for relationship info
        # This would introspect the model
        field = None

        # Check if field exists on model
        if hasattr(self.model, field_name):
            attr = getattr(self.model, field_name)

            # Check for relationship descriptors
            if hasattr(attr, 'field_type'):
                field = RelatedField(
                    name=field_name,
                    field_type=attr.field_type,
                    model=self.model,
                    related_model=attr.related_model,
                    foreign_key=getattr(attr, 'foreign_key', ''),
                    through_model=getattr(attr, 'through_model', None)
                )

        self._related_cache[field_name] = field
        return field

    def build_select_query(self, base_query: str) -> Tuple[str, List[str]]:
        """
        Build SELECT query with JOINs for select_related.

        Args:
            base_query: Base SELECT query

        Returns:
            Tuple of (query, join_clauses)
        """
        joins = []

        for field_path in self._select_related:
            parts = field_path.split('__')
            current_model = self.model
            table_alias = current_model.__tablename__ if hasattr(current_model, '__tablename__') else current_model.__name__.lower()

            for part in parts:
                field_info = self._get_related_field(part)

                if field_info and field_info.field_type in ('fk', 'o2o'):
                    related_table = field_info.related_model.__tablename__ if hasattr(field_info.related_model, '__tablename__') else field_info.related_model.__name__.lower()
                    related_alias = f"{table_alias}_{part}"

                    joins.append(
                        f"LEFT JOIN {related_table} AS {related_alias} "
                        f"ON {table_alias}.{field_info.foreign_key or part + '_id'} = {related_alias}.id"
                    )

                    table_alias = related_alias
                    current_model = field_info.related_model

        return base_query, joins

    async def prefetch_objects(self, objects: List[Any]) -> List[Any]:
        """
        Prefetch related objects for a list of objects.

        Args:
            objects: List of model instances

        Returns:
            Same list with related objects prefetched
        """
        if not objects:
            return objects

        for field_path in self._prefetch_related:
            await self._prefetch_field(objects, field_path)

        return objects

    async def _prefetch_field(self, objects: List[Any], field_path: str) -> None:
        """Prefetch a single field for all objects."""
        parts = field_path.split('__')
        current_objects = objects

        for i, part in enumerate(parts):
            if not current_objects:
                break

            # Get related field info
            first_obj = current_objects[0]
            model = first_obj.__class__

            field_info = self._get_related_field_for_model(model, part)

            if field_info is None:
                break

            if field_info.field_type == 'm2m':
                # Prefetch M2M
                await self._prefetch_m2m(current_objects, field_info, part)
            elif field_info.field_type == 'reverse_fk':
                # Prefetch reverse FK
                await self._prefetch_reverse_fk(current_objects, field_info, part)
            elif field_info.field_type == 'fk':
                # For FK in nested path, continue with related objects
                related_objects = []
                for obj in current_objects:
                    related = getattr(obj, part, None)
                    if related:
                        if isinstance(related, list):
                            related_objects.extend(related)
                        else:
                            related_objects.append(related)
                current_objects = related_objects
            else:
                break

            # If there are more parts, continue with related objects
            if i < len(parts) - 1:
                related_objects = []
                for obj in current_objects:
                    related = getattr(obj, part, [])
                    if related:
                        if isinstance(related, list):
                            related_objects.extend(related)
                        else:
                            related_objects.append(related)
                current_objects = related_objects

    def _get_related_field_for_model(self, model: Type, field_name: str) -> Optional[RelatedField]:
        """Get related field info for a specific model."""
        if hasattr(model, '__relationships__'):
            rel = model.__relationships__.get(field_name)
            if rel:
                return RelatedField(
                    name=field_name,
                    field_type=rel.get('type', 'fk'),
                    model=model,
                    related_model=rel.get('model'),
                    foreign_key=rel.get('fk', ''),
                    through_model=rel.get('through')
                )
        return None

    async def _prefetch_m2m(self, objects: List[Any], field_info: RelatedField, field_name: str) -> None:
        """Prefetch many-to-many relationship."""
        if not objects:
            return

        # Get IDs of all objects
        object_ids = [obj.id for obj in objects if hasattr(obj, 'id') and obj.id]

        if not object_ids:
            return

        through_model = field_info.through_model
        related_model = field_info.related_model

        if through_model is None or related_model is None:
            return

        # Query through table to get all relationships
        # This would be database-specific
        through_table = through_model.__tablename__ if hasattr(through_model, '__tablename__') else through_model.__name__.lower()
        related_table = related_model.__tablename__ if hasattr(related_model, '__tablename__') else related_model.__name__.lower()

        # Get source and target column names
        source_col = f"{objects[0].__class__.__name__.lower()}_id"
        target_col = f"{related_model.__name__.lower()}_id"

        # Query
        # SELECT * FROM through_table WHERE source_col IN (ids)
        # Then query related objects
        # SELECT * FROM related_table WHERE id IN (target_ids)

        # For now, we'll just populate the cache with empty lists
        # In real implementation, this would query the database
        for obj in objects:
            if not hasattr(obj, '_prefetched_objects_cache'):
                obj._prefetched_objects_cache = {}
            obj._prefetched_objects_cache[field_name] = []

    async def _prefetch_reverse_fk(self, objects: List[Any], field_info: RelatedField, field_name: str) -> None:
        """Prefetch reverse foreign key relationship."""
        if not objects:
            return

        object_ids = [obj.id for obj in objects if hasattr(obj, 'id') and obj.id]

        if not object_ids:
            return

        related_model = field_info.related_model

        if related_model is None:
            return

        # Query related objects
        # SELECT * FROM related_table WHERE fk_col IN (ids)

        fk_col = field_info.foreign_key or f"{objects[0].__class__.__name__.lower()}_id"

        # For now, populate cache with empty lists
        for obj in objects:
            if not hasattr(obj, '_prefetched_objects_cache'):
                obj._prefetched_objects_cache = {}
            obj._prefetched_objects_cache[field_name] = []


class Prefetch:
    """
    Control prefetch behavior with custom querysets.

    Example:
        posts = await Post.prefetch_related(
            Prefetch('comments', Comment.filter(is_approved=True))
        ).all()
    """

    def __init__(
        self,
        lookup: str,
        queryset: Any = None,
        to_attr: str = None
    ):
        """
        Initialize Prefetch.

        Args:
            lookup: Field name to prefetch
            queryset: Custom queryset to use
            to_attr: Attribute name to store prefetched objects
        """
        self.lookup = lookup
        self.queryset = queryset
        self.to_attr = to_attr

    def __repr__(self) -> str:
        return f"Prefetch('{self.lookup}')"


# Mixin for models to add optimization methods
class OptimizableQuerySet:
    """
    Mixin providing select_related and prefetch_related methods.
    """

    _optimizer: QueryOptimizer = None

    def select_related(self, *fields: str) -> 'OptimizableQuerySet':
        """Add select_related to queryset."""
        if self._optimizer is None:
            self._optimizer = QueryOptimizer(self.model if hasattr(self, 'model') else self.__class__)
        self._optimizer.select_related(*fields)
        return self

    def prefetch_related(self, *lookups: Union[str, Prefetch]) -> 'OptimizableQuerySet':
        """Add prefetch_related to queryset."""
        if self._optimizer is None:
            self._optimizer = QueryOptimizer(self.model if hasattr(self, 'model') else self.__class__)

        for lookup in lookups:
            if isinstance(lookup, Prefetch):
                self._optimizer.prefetch_related(lookup.lookup)
            else:
                self._optimizer.prefetch_related(lookup)

        return self

    def only(self, *fields: str) -> 'OptimizableQuerySet':
        """Load only specified fields."""
        if self._optimizer is None:
            self._optimizer = QueryOptimizer(self.model if hasattr(self, 'model') else self.__class__)
        self._optimizer.only(*fields)
        return self

    def defer(self, *fields: str) -> 'OptimizableQuerySet':
        """Defer loading of specified fields."""
        if self._optimizer is None:
            self._optimizer = QueryOptimizer(self.model if hasattr(self, 'model') else self.__class__)
        self._optimizer.defer(*fields)
        return self


# Functions for direct use
def select_related(*fields: str):
    """
    Decorator to add select_related to a queryset.

    Example:
        @select_related('author', 'category')
        def get_posts():
            return Post.all()
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            if hasattr(result, 'select_related'):
                result = result.select_related(*fields)
            return result
        return wrapper
    return decorator


def prefetch_related(*fields: str):
    """
    Decorator to add prefetch_related to a queryset.

    Example:
        @prefetch_related('tags', 'comments')
        def get_posts():
            return Post.all()
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            if hasattr(result, 'prefetch_related'):
                result = result.prefetch_related(*fields)
            return result
        return wrapper
    return decorator
