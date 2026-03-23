"""
FastStack ORM Aggregation API

Provides aggregate functions and annotations for database queries.
Django-compatible but async-first design.

Features:
- Aggregate functions: Count, Sum, Avg, Min, Max, StdDev, Variance
- Annotation support for per-row computed values
- Q objects for conditional aggregation
- QuerySet-like interface with aggregate(), annotate(), values(), values_list()

Example:
    # Aggregation
    result = await Book.objects.aggregate(
        Count('id'), 
        avg_price=Avg('price')
    )
    # Returns: {'id__count': 5, 'avg_price': 25.50}

    # Annotation
    authors = await Author.objects.annotate(book_count=Count('books'))
    # Each author has .book_count attribute
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar, Union, TYPE_CHECKING
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from sqlmodel import Session, SQLModel, select, func, col
from sqlalchemy import ColumnElement, Select, Label
from sqlalchemy.sql import functions as sa_func
from sqlalchemy.orm import InstrumentedAttribute

if TYPE_CHECKING:
    from faststack.orm.base import BaseModel

T = TypeVar("T", bound=SQLModel)


# =============================================================================
# Q Objects for Filtering
# =============================================================================

class Q:
    """
    Q object for building complex query conditions.
    
    Used for conditional aggregation and filtering.
    
    Example:
        # Count books with price > 100
        Count('id', filter=Q(price__gt=100))
        
        # Complex conditions
        Q(price__gt=100) & Q(is_active=True)
        Q(price__lt=50) | Q(price__gt=200)
    """
    
    def __init__(
        self, 
        *args: "Q", 
        _connector: str = "AND",
        _negated: bool = False,
        **kwargs: Any
    ):
        """
        Initialize Q object.
        
        Args:
            *args: Child Q objects for combining conditions
            _connector: "AND" or "OR" for combining conditions
            _negated: Whether to negate this condition (NOT)
            **kwargs: Field lookups (field=value, field__gt=value, etc.)
        """
        self.children = list(args)
        self.connector = _connector
        self.negated = _negated
        self.lookups = kwargs
    
    def __and__(self, other: "Q") -> "Q":
        """Combine with AND."""
        return Q(self, other, _connector="AND")
    
    def __or__(self, other: "Q") -> "Q":
        """Combine with OR."""
        return Q(self, other, _connector="OR")
    
    def __invert__(self) -> "Q":
        """Negate the condition (NOT)."""
        return Q(
            *self.children,
            _connector=self.connector,
            _negated=not self.negated,
            **self.lookups
        )
    
    def to_where_clause(self, model: type[SQLModel]) -> ColumnElement[bool] | None:
        """
        Convert Q object to SQLAlchemy where clause.
        
        Args:
            model: The SQLModel class to apply conditions to
            
        Returns:
            SQLAlchemy ColumnElement for use in where()
        """
        conditions: list[ColumnElement[bool]] = []
        
        # Process lookups
        for lookup, value in self.lookups.items():
            condition = self._process_lookup(model, lookup, value)
            if condition is not None:
                conditions.append(condition)
        
        # Process child Q objects
        for child in self.children:
            child_condition = child.to_where_clause(model)
            if child_condition is not None:
                conditions.append(child_condition)
        
        if not conditions:
            return None
        
        # Combine conditions
        if self.connector == "OR":
            result = conditions[0]
            for c in conditions[1:]:
                result = result | c
        else:
            result = conditions[0]
            for c in conditions[1:]:
                result = result & c
        
        # Apply negation
        if self.negated:
            result = ~result
        
        return result
    
    def _process_lookup(
        self, 
        model: type[SQLModel], 
        lookup: str, 
        value: Any
    ) -> ColumnElement[bool] | None:
        """
        Process a single lookup into a condition.
        
        Supports Django-style lookups:
        - field=value: Exact match
        - field__gt=value: Greater than
        - field__gte=value: Greater than or equal
        - field__lt=value: Less than
        - field__lte=value: Less than or equal
        - field__in=value: In list
        - field__isnull=value: Is null
        - field__contains=value: Contains (case-sensitive)
        - field__icontains=value: Contains (case-insensitive)
        - field__startswith=value: Starts with
        - field__endswith=value: Ends with
        """
        parts = lookup.split("__")
        field_name = parts[0]
        lookup_type = parts[1] if len(parts) > 1 else "exact"
        
        if not hasattr(model, field_name):
            return None
        
        column = getattr(model, field_name)
        
        if lookup_type == "exact":
            return column == value
        elif lookup_type == "gt":
            return column > value
        elif lookup_type == "gte":
            return column >= value
        elif lookup_type == "lt":
            return column < value
        elif lookup_type == "lte":
            return column <= value
        elif lookup_type == "in":
            return column.in_(value)
        elif lookup_type == "isnull":
            return column.is_(None) if value else column.isnot(None)
        elif lookup_type == "contains":
            return col(column).contains(value)
        elif lookup_type == "icontains":
            return col(column).icontains(value)
        elif lookup_type == "startswith":
            return col(column).startswith(value)
        elif lookup_type == "endswith":
            return col(column).endswith(value)
        
        return column == value


# =============================================================================
# Aggregate Functions
# =============================================================================

class Aggregate:
    """
    Base class for SQL aggregate functions.
    
    Attributes:
        function: SQL function name (e.g., 'COUNT', 'SUM')
        template: SQL template for custom aggregates
        distinct: Whether to use DISTINCT
        filter: Optional Q object for conditional aggregation
        source: The field name to aggregate
        alias: The alias for the result (auto-generated if not provided)
    
    Example:
        Count('id')
        Sum('price', distinct=True)
        Avg('age', filter=Q(is_active=True))
    """
    
    function: str = ""
    template: str = "%(function)s(%(distinct)s%(field)s)"
    name: str = ""
    
    def __init__(
        self,
        field: str,
        *,
        distinct: bool = False,
        filter: Q | None = None,
        output_field: type | None = None,
    ):
        """
        Initialize aggregate function.
        
        Args:
            field: The field name to aggregate
            distinct: Whether to use DISTINCT
            filter: Optional Q object for conditional aggregation
            output_field: The Python type for the result
        """
        self.source = field
        self.distinct = distinct
        self.filter = filter
        self.output_field = output_field
        self.alias: str | None = None
        self._expressions: list[Aggregate] = []
    
    def set_alias(self, alias: str) -> "Aggregate":
        """Set the alias for this aggregate."""
        self.alias = alias
        return self
    
    def get_alias(self) -> str:
        """Get the alias for this aggregate."""
        if self.alias:
            return self.alias
        # Generate default alias: field__function
        return f"{self.source}__{self.name or self.function.lower()}"
    
    def to_sqlalchemy(
        self, 
        model: type[SQLModel]
    ) -> Label[Any]:
        """
        Convert aggregate to SQLAlchemy expression.
        
        Args:
            model: The SQLModel class
            
        Returns:
            SQLAlchemy labeled expression
        """
        # Get the column
        if self.source == "*":
            column = sa_func.count() if self.function == "COUNT" else None
            if column is None:
                # For other functions with *, we need special handling
                column = sa_func.literal_column("*")
        elif hasattr(model, self.source):
            column = getattr(model, self.source)
        else:
            raise ValueError(f"Field '{self.source}' not found on model {model.__name__}")
        
        # Build the function expression
        if self.distinct:
            if self.source == "*":
                raise ValueError("DISTINCT cannot be used with COUNT(*)")
            expr = self._build_distinct_func(column)
        else:
            expr = self._build_func(column)
        
        # Apply filter if present
        if self.filter:
            where_clause = self.filter.to_where_clause(model)
            if where_clause is not None:
                expr = sa_func.filter(expr, where_clause)
        
        return expr.label(self.get_alias())
    
    def _build_func(self, column: Any) -> Any:
        """Build the aggregate function expression."""
        if self.function == "COUNT":
            return sa_func.count(column)
        elif self.function == "SUM":
            return sa_func.sum(column)
        elif self.function == "AVG":
            return sa_func.avg(column)
        elif self.function == "MIN":
            return sa_func.min(column)
        elif self.function == "MAX":
            return sa_func.max(column)
        elif self.function == "STDDEV":
            return sa_func.stddev(column)
        elif self.function == "VARIANCE":
            return sa_func.variance(column)
        else:
            # Generic function
            return sa_func.literal_column(
                self.template % {
                    "function": self.function,
                    "field": str(column),
                    "distinct": "DISTINCT " if self.distinct else ""
                }
            )
    
    def _build_distinct_func(self, column: Any) -> Any:
        """Build distinct aggregate function expression."""
        if self.function == "COUNT":
            return sa_func.count(column.distinct())
        elif self.function == "SUM":
            return sa_func.sum(column.distinct())
        elif self.function == "AVG":
            return sa_func.avg(column.distinct())
        else:
            # Generic distinct handling
            return sa_func.literal_column(
                f"{self.function}(DISTINCT {column})"
            )


class Count(Aggregate):
    """
    COUNT aggregate function.
    
    Example:
        Count('id')  # COUNT(id)
        Count('id', distinct=True)  # COUNT(DISTINCT id)
        Count('*', filter=Q(is_active=True))  # Conditional count
    """
    
    function = "COUNT"
    name = "count"
    
    def __init__(
        self,
        field: str = "*",
        *,
        distinct: bool = False,
        filter: Q | None = None,
    ):
        super().__init__(field, distinct=distinct, filter=filter)
    
    def _build_func(self, column: Any) -> Any:
        if self.source == "*":
            return sa_func.count()
        return sa_func.count(column)


class Sum(Aggregate):
    """
    SUM aggregate function.
    
    Example:
        Sum('price')  # SUM(price)
        Sum('amount', distinct=True)  # SUM(DISTINCT amount)
    """
    
    function = "SUM"
    name = "sum"


class Avg(Aggregate):
    """
    AVG aggregate function for average.
    
    Example:
        Avg('price')  # AVG(price)
        Avg('rating', filter=Q(is_verified=True))
    """
    
    function = "AVG"
    name = "avg"


class Min(Aggregate):
    """
    MIN aggregate function.
    
    Example:
        Min('price')  # MIN(price)
    """
    
    function = "MIN"
    name = "min"


class Max(Aggregate):
    """
    MAX aggregate function.
    
    Example:
        Max('price')  # MAX(price)
    """
    
    function = "MAX"
    name = "max"


class StdDev(Aggregate):
    """
    Standard deviation aggregate function.
    
    Args:
        field: The field to calculate standard deviation for
        sample: If True, use sample standard deviation (STDDEV_SAMP)
                If False, use population standard deviation (STDDEV_POP)
    
    Example:
        StdDev('score')  # Population standard deviation
        StdDev('score', sample=True)  # Sample standard deviation
    """
    
    function = "STDDEV"
    name = "stddev"
    
    def __init__(
        self,
        field: str,
        *,
        sample: bool = False,
        distinct: bool = False,
        filter: Q | None = None,
    ):
        super().__init__(field, distinct=distinct, filter=filter)
        self.sample = sample
    
    def _build_func(self, column: Any) -> Any:
        if self.sample:
            return sa_func.stddev_samp(column)
        return sa_func.stddev_pop(column)


class Variance(Aggregate):
    """
    Variance aggregate function.
    
    Args:
        field: The field to calculate variance for
        sample: If True, use sample variance (VAR_SAMP)
                If False, use population variance (VAR_POP)
    
    Example:
        Variance('score')  # Population variance
        Variance('score', sample=True)  # Sample variance
    """
    
    function = "VARIANCE"
    name = "variance"
    
    def __init__(
        self,
        field: str,
        *,
        sample: bool = False,
        distinct: bool = False,
        filter: Q | None = None,
    ):
        super().__init__(field, distinct=distinct, filter=filter)
        self.sample = sample
    
    def _build_func(self, column: Any) -> Any:
        if self.sample:
            return sa_func.var_samp(column)
        return sa_func.var_pop(column)


# =============================================================================
# Annotation
# =============================================================================

class Annotation:
    """
    Annotation for per-row computed values.
    
    Similar to Aggregate but returns per-row values instead of a single value.
    
    Example:
        Author.objects.annotate(book_count=Count('books'))
        # Each author will have .book_count attribute
    """
    
    def __init__(
        self,
        expression: Aggregate | ColumnElement[Any],
        *,
        alias: str | None = None,
    ):
        """
        Initialize annotation.
        
        Args:
            expression: The aggregate or SQLAlchemy expression
            alias: The name for the computed field
        """
        self.expression = expression
        self.alias = alias
    
    def to_sqlalchemy(self, model: type[SQLModel]) -> Label[Any]:
        """
        Convert annotation to SQLAlchemy expression.
        
        Args:
            model: The SQLModel class
            
        Returns:
            SQLAlchemy labeled expression
        """
        if isinstance(self.expression, Aggregate):
            if self.alias:
                self.expression.set_alias(self.alias)
            return self.expression.to_sqlalchemy(model)
        else:
            return self.expression.label(self.alias)


# =============================================================================
# QuerySet-like Class
# =============================================================================

class QuerySet(Generic[T]):
    """
    Async-first QuerySet for database queries.
    
    Provides Django-like API for building and executing queries.
    Supports chaining for complex queries.
    
    Example:
        # Basic queries
        books = await Book.objects.all()
        book = await Book.objects.filter(title="Dune").first()
        
        # Aggregation
        stats = await Book.objects.aggregate(
            Count('id'), 
            avg_price=Avg('price')
        )
        
        # Annotation
        authors = await Author.objects.annotate(
            book_count=Count('books')
        )
        
        # Values
        for row in await Book.objects.values('title', 'price'):
            print(row['title'], row['price'])
    """
    
    def __init__(
        self,
        model: type[T],
        session: Session | None = None,
    ):
        """
        Initialize QuerySet.
        
        Args:
            model: The SQLModel class to query
            session: Optional database session (for async context)
        """
        self.model = model
        self._session = session
        self._filters: list[ColumnElement[bool]] = []
        self._excludes: list[ColumnElement[bool]] = []
        self._order_by: list[Any] = []
        self._limit: int | None = None
        self._offset: int | None = None
        self._annotations: list[Annotation] = []
        self._values_fields: list[str] = []
        self._values_list_fields: list[str] = []
        self._flat: bool = False
        self._group_by_fields: list[str] = []
        self._distinct: bool = False
        self._select_related: list[str] = []
        self._prefetch_related: list[str] = []
    
    def _clone(self) -> "QuerySet[T]":
        """Create a copy of this QuerySet."""
        clone = QuerySet(self.model, self._session)
        clone._filters = self._filters.copy()
        clone._excludes = self._excludes.copy()
        clone._order_by = self._order_by.copy()
        clone._limit = self._limit
        clone._offset = self._offset
        clone._annotations = self._annotations.copy()
        clone._values_fields = self._values_fields.copy()
        clone._values_list_fields = self._values_list_fields.copy()
        clone._flat = self._flat
        clone._group_by_fields = self._group_by_fields.copy()
        clone._distinct = self._distinct
        clone._select_related = self._select_related.copy()
        clone._prefetch_related = self._prefetch_related.copy()
        return clone
    
    # =========================================================================
    # Filtering Methods
    # =========================================================================
    
    def filter(self, *args: Q | ColumnElement[bool], **kwargs: Any) -> "QuerySet[T]":
        """
        Filter results by conditions.
        
        Args:
            *args: Q objects or SQLAlchemy conditions
            **kwargs: Field=value conditions
            
        Returns:
            New QuerySet with filters applied
            
        Example:
            Book.objects.filter(price__gt=100, is_active=True)
            Book.objects.filter(Q(price__gt=100) | Q(rating__gte=4))
        """
        clone = self._clone()
        
        for arg in args:
            if isinstance(arg, Q):
                condition = arg.to_where_clause(self.model)
                if condition is not None:
                    clone._filters.append(condition)
            else:
                clone._filters.append(arg)
        
        for key, value in kwargs.items():
            q = Q(**{key: value})
            condition = q.to_where_clause(self.model)
            if condition is not None:
                clone._filters.append(condition)
        
        return clone
    
    def exclude(self, *args: Q | ColumnElement[bool], **kwargs: Any) -> "QuerySet[T]":
        """
        Exclude results matching conditions.
        
        Args:
            *args: Q objects or SQLAlchemy conditions
            **kwargs: Field=value conditions
            
        Returns:
            New QuerySet with exclusions applied
        """
        clone = self._clone()
        
        for arg in args:
            if isinstance(arg, Q):
                condition = ~arg.to_where_clause(self.model)
                if condition is not None:
                    clone._excludes.append(condition)
            else:
                clone._excludes.append(~arg)
        
        for key, value in kwargs.items():
            q = Q(**{key: value})
            condition = q.to_where_clause(self.model)
            if condition is not None:
                clone._excludes.append(~condition)
        
        return clone
    
    def order_by(self, *fields: str | InstrumentedAttribute) -> "QuerySet[T]":
        """
        Order results by fields.
        
        Prefix with '-' for descending order.
        
        Args:
            *fields: Field names (prefix with '-' for descending)
            
        Returns:
            New QuerySet with ordering applied
            
        Example:
            Book.objects.order_by('title')
            Book.objects.order_by('-price', 'title')
        """
        clone = self._clone()
        
        for field in fields:
            if isinstance(field, str):
                if field.startswith("-"):
                    field_name = field[1:]
                    if hasattr(self.model, field_name):
                        clone._order_by.append(getattr(self.model, field_name).desc())
                else:
                    if hasattr(self.model, field):
                        clone._order_by.append(getattr(self.model, field))
            else:
                clone._order_by.append(field)
        
        return clone
    
    def limit(self, n: int) -> "QuerySet[T]":
        """Limit the number of results."""
        clone = self._clone()
        clone._limit = n
        return clone
    
    def offset(self, n: int) -> "QuerySet[T]":
        """Offset the results."""
        clone = self._clone()
        clone._offset = n
        return clone
    
    def distinct(self) -> "QuerySet[T]":
        """Return distinct results."""
        clone = self._clone()
        clone._distinct = True
        return clone
    
    # =========================================================================
    # Aggregation Methods
    # =========================================================================
    
    def aggregate(
        self, 
        *args: Aggregate, 
        **kwargs: Aggregate
    ) -> dict[str, Any]:
        """
        Return a dictionary of aggregate values.
        
        This is a synchronous method that requires a session.
        For async usage, use aaggregate().
        
        Args:
            *args: Aggregate functions
            **kwargs: Named aggregate functions
            
        Returns:
            Dictionary of aggregate results
            
        Example:
            Book.objects.aggregate(
                Count('id'), 
                avg_price=Avg('price')
            )
            # Returns: {'id__count': 5, 'avg_price': 25.50}
        """
        if not self._session:
            raise RuntimeError("No session available. Use with session context.")
        
        # Build select with aggregates
        statement = select(*[
            agg.set_alias(alias).to_sqlalchemy(self.model) if alias else agg.to_sqlalchemy(self.model)
            for alias, agg in self._get_aggregates(args, kwargs)
        ])
        
        # Apply filters
        for f in self._filters:
            statement = statement.where(f)
        
        result = self._session.exec(statement).one()
        
        # Convert to dictionary
        if hasattr(result, '_asdict'):
            return dict(result._asdict())
        return dict(result._mapping) if hasattr(result, '_mapping') else dict(zip(
            [agg.get_alias() for _, agg in self._get_aggregates(args, kwargs)],
            result if isinstance(result, tuple) else [result]
        ))
    
    async def aaggregate(
        self, 
        *args: Aggregate, 
        **kwargs: Aggregate
    ) -> dict[str, Any]:
        """
        Async version of aggregate().
        
        Returns aggregate values asynchronously.
        """
        # This would use async session in production
        # For now, delegate to sync version
        return self.aggregate(*args, **kwargs)
    
    def _get_aggregates(
        self,
        args: tuple[Aggregate, ...],
        kwargs: dict[str, Aggregate]
    ) -> list[tuple[str | None, Aggregate]]:
        """Get list of (alias, aggregate) tuples."""
        aggregates: list[tuple[str | None, Aggregate]] = []
        
        for agg in args:
            aggregates.append((None, agg))
        
        for alias, agg in kwargs.items():
            aggregates.append((alias, agg))
        
        return aggregates
    
    # =========================================================================
    # Annotation Methods
    # =========================================================================
    
    def annotate(
        self, 
        *args: Annotation | Aggregate,
        **kwargs: Annotation | Aggregate
    ) -> "QuerySet[T]":
        """
        Add computed fields to each row.
        
        Args:
            *args: Annotation or Aggregate objects
            **kwargs: Named annotations
            
        Returns:
            New QuerySet with annotations
            
        Example:
            Author.objects.annotate(
                book_count=Count('books')
            )
        """
        clone = self._clone()
        
        for annotation in args:
            if isinstance(annotation, Aggregate):
                clone._annotations.append(Annotation(annotation))
            else:
                clone._annotations.append(annotation)
        
        for alias, annotation in kwargs.items():
            if isinstance(annotation, Aggregate):
                clone._annotations.append(Annotation(annotation, alias=alias))
            else:
                annotation.alias = alias
                clone._annotations.append(annotation)
        
        return clone
    
    # =========================================================================
    # Group By Methods
    # =========================================================================
    
    def group_by(self, *fields: str) -> "QuerySet[T]":
        """
        Group results by fields.
        
        Usually used with annotate() for custom GROUP BY.
        
        Args:
            *fields: Field names to group by
            
        Returns:
            New QuerySet with group by applied
            
        Example:
            Book.objects.group_by('category').annotate(
                count=Count('id')
            )
        """
        clone = self._clone()
        clone._group_by_fields = list(fields)
        return clone
    
    # =========================================================================
    # Values Methods
    # =========================================================================
    
    def values(self, *fields: str) -> "ValuesQuerySet[T]":
        """
        Return dictionaries instead of models.
        
        Args:
            *fields: Field names to include (empty = all fields)
            
        Returns:
            ValuesQuerySet that returns dicts
            
        Example:
            Book.objects.values('title', 'price')
            # Returns: [{'title': 'Dune', 'price': 25.0}, ...]
        """
        return ValuesQuerySet(
            self.model,
            self._session,
            fields=list(fields),
            filters=self._filters,
            excludes=self._excludes,
            order_by=self._order_by,
            limit=self._limit,
            offset=self._offset,
            annotations=self._annotations,
            group_by_fields=self._group_by_fields,
            distinct=self._distinct,
        )
    
    def values_list(self, *fields: str, flat: bool = False) -> "ValuesListQuerySet[T]":
        """
        Return tuples instead of models.
        
        Args:
            *fields: Field names to include
            flat: If True and single field, return flat list
            
        Returns:
            ValuesListQuerySet that returns tuples
            
        Example:
            Book.objects.values_list('title', 'price')
            # Returns: [('Dune', 25.0), ...]
            
            Book.objects.values_list('title', flat=True)
            # Returns: ['Dune', ...]
        """
        return ValuesListQuerySet(
            self.model,
            self._session,
            fields=list(fields),
            flat=flat,
            filters=self._filters,
            excludes=self._excludes,
            order_by=self._order_by,
            limit=self._limit,
            offset=self._offset,
            annotations=self._annotations,
            group_by_fields=self._group_by_fields,
            distinct=self._distinct,
        )
    
    # =========================================================================
    # Execution Methods
    # =========================================================================
    
    def all(self) -> list[T]:
        """
        Get all results.
        
        Returns:
            List of model instances
        """
        if not self._session:
            raise RuntimeError("No session available. Use with session context.")
        
        statement = self._build_statement()
        return list(self._session.exec(statement).all())
    
    async def aall(self) -> list[T]:
        """Async version of all()."""
        # This would use async session in production
        return self.all()
    
    def first(self) -> T | None:
        """
        Get the first result.
        
        Returns:
            First model instance or None
        """
        if not self._session:
            raise RuntimeError("No session available. Use with session context.")
        
        statement = self._build_statement()
        return self._session.exec(statement).first()
    
    async def afirst(self) -> T | None:
        """Async version of first()."""
        return self.first()
    
    def one(self) -> T:
        """
        Get exactly one result.
        
        Raises:
            sqlalchemy.exc.NoResultFound: No results
            sqlalchemy.exc.MultipleResultsFound: Multiple results
        """
        if not self._session:
            raise RuntimeError("No session available. Use with session context.")
        
        statement = self._build_statement()
        return self._session.exec(statement).one()
    
    async def aone(self) -> T:
        """Async version of one()."""
        return self.one()
    
    def count(self) -> int:
        """
        Count results.
        
        Returns:
            Number of matching records
        """
        if not self._session:
            raise RuntimeError("No session available. Use with session context.")
        
        statement = select(func.count()).select_from(self.model)
        
        for f in self._filters:
            statement = statement.where(f)
        
        for f in self._excludes:
            statement = statement.where(f)
        
        return self._session.exec(statement).one()
    
    async def acount(self) -> int:
        """Async version of count()."""
        return self.count()
    
    def exists(self) -> bool:
        """
        Check if any results exist.
        
        Returns:
            True if any results exist
        """
        return self.count() > 0
    
    async def aexists(self) -> bool:
        """Async version of exists()."""
        return self.exists()
    
    def _build_statement(self) -> Select:
        """Build the SQLAlchemy select statement."""
        statement = select(self.model)
        
        # Apply filters
        for f in self._filters:
            statement = statement.where(f)
        
        for f in self._excludes:
            statement = statement.where(f)
        
        # Apply annotations
        if self._annotations:
            for annotation in self._annotations:
                statement = statement.add_columns(
                    annotation.to_sqlalchemy(self.model)
                )
            
            # GROUP BY for annotations (unless explicit)
            if not self._group_by_fields:
                # Auto GROUP BY on primary key
                if hasattr(self.model, 'id'):
                    statement = statement.group_by(self.model.id)
            else:
                for field in self._group_by_fields:
                    if hasattr(self.model, field):
                        statement = statement.group_by(getattr(self.model, field))
        
        # Apply ordering
        for order in self._order_by:
            statement = statement.order_by(order)
        
        # Apply limit/offset
        if self._limit is not None:
            statement = statement.limit(self._limit)
        if self._offset is not None:
            statement = statement.offset(self._offset)
        
        # Apply distinct
        if self._distinct:
            statement = statement.distinct()
        
        return statement
    
    # =========================================================================
    # Iterator Methods
    # =========================================================================
    
    def __iter__(self):
        """Iterate over results."""
        return iter(self.all())
    
    async def __aiter__(self) -> AsyncIterator[T]:
        """Async iterate over results."""
        for item in self.all():
            yield item
    
    # =========================================================================
    # Context Manager Support
    # =========================================================================
    
    def using(self, session: Session) -> "QuerySet[T]":
        """
        Use a specific session for this query.
        
        Args:
            session: Database session
            
        Returns:
            QuerySet with session attached
        """
        clone = self._clone()
        clone._session = session
        return clone


class ValuesQuerySet(Generic[T]):
    """
    QuerySet that returns dictionaries instead of models.
    """
    
    def __init__(
        self,
        model: type[T],
        session: Session | None = None,
        *,
        fields: list[str] | None = None,
        filters: list[ColumnElement[bool]] | None = None,
        excludes: list[ColumnElement[bool]] | None = None,
        order_by: list[Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        annotations: list[Annotation] | None = None,
        group_by_fields: list[str] | None = None,
        distinct: bool = False,
    ):
        self.model = model
        self._session = session
        self._fields = fields or []
        self._filters = filters or []
        self._excludes = excludes or []
        self._order_by = order_by or []
        self._limit = limit
        self._offset = offset
        self._annotations = annotations or []
        self._group_by_fields = group_by_fields or []
        self._distinct = distinct
    
    def _clone(self, **kwargs: Any) -> "ValuesQuerySet[T]":
        """Clone this ValuesQuerySet."""
        return ValuesQuerySet(
            self.model,
            self._session,
            fields=kwargs.get('fields', self._fields.copy()),
            filters=kwargs.get('filters', self._filters.copy()),
            excludes=kwargs.get('excludes', self._excludes.copy()),
            order_by=kwargs.get('order_by', self._order_by.copy()),
            limit=kwargs.get('limit', self._limit),
            offset=kwargs.get('offset', self._offset),
            annotations=kwargs.get('annotations', self._annotations.copy()),
            group_by_fields=kwargs.get('group_by_fields', self._group_by_fields.copy()),
            distinct=kwargs.get('distinct', self._distinct),
        )
    
    def filter(self, *args: Q | ColumnElement[bool], **kwargs: Any) -> "ValuesQuerySet[T]":
        """Add filter conditions."""
        clone = self._clone()
        for arg in args:
            if isinstance(arg, Q):
                condition = arg.to_where_clause(self.model)
                if condition is not None:
                    clone._filters.append(condition)
            else:
                clone._filters.append(arg)
        for key, value in kwargs.items():
            q = Q(**{key: value})
            condition = q.to_where_clause(self.model)
            if condition is not None:
                clone._filters.append(condition)
        return clone
    
    def annotate(
        self, 
        *args: Annotation | Aggregate,
        **kwargs: Annotation | Aggregate
    ) -> "ValuesQuerySet[T]":
        """Add annotations."""
        clone = self._clone()
        for annotation in args:
            if isinstance(annotation, Aggregate):
                clone._annotations.append(Annotation(annotation))
            else:
                clone._annotations.append(annotation)
        for alias, annotation in kwargs.items():
            if isinstance(annotation, Aggregate):
                clone._annotations.append(Annotation(annotation, alias=alias))
            else:
                annotation.alias = alias
                clone._annotations.append(annotation)
        return clone
    
    def _build_statement(self) -> Select:
        """Build the SQLAlchemy select statement."""
        # Determine columns to select
        if self._fields:
            columns = [
                getattr(self.model, f) 
                for f in self._fields 
                if hasattr(self.model, f)
            ]
        else:
            columns = [self.model]
        
        statement = select(*columns)
        
        # Add annotations
        for annotation in self._annotations:
            statement = statement.add_columns(
                annotation.to_sqlalchemy(self.model)
            )
        
        # Apply filters
        for f in self._filters:
            statement = statement.where(f)
        for f in self._excludes:
            statement = statement.where(f)
        
        # GROUP BY for annotations or when grouping
        group_fields = self._group_by_fields or self._fields
        if group_fields:
            for field in group_fields:
                if hasattr(self.model, field):
                    statement = statement.group_by(getattr(self.model, field))
        
        # Apply ordering
        for order in self._order_by:
            statement = statement.order_by(order)
        
        # Apply limit/offset
        if self._limit is not None:
            statement = statement.limit(self._limit)
        if self._offset is not None:
            statement = statement.offset(self._offset)
        
        # Apply distinct
        if self._distinct:
            statement = statement.distinct()
        
        return statement
    
    def all(self) -> list[dict[str, Any]]:
        """Get all results as dictionaries."""
        if not self._session:
            raise RuntimeError("No session available.")
        
        statement = self._build_statement()
        results = self._session.exec(statement).all()
        
        # Convert to dictionaries
        field_names = self._fields or [c.name for c in self.model.__table__.columns]
        annotation_names = [a.alias for a in self._annotations]
        all_names = field_names + annotation_names
        
        dicts = []
        for row in results:
            if hasattr(row, '_asdict'):
                dicts.append(dict(row._asdict()))
            elif hasattr(row, '_mapping'):
                dicts.append(dict(row._mapping))
            elif isinstance(row, dict):
                dicts.append(row)
            else:
                # Tuple result
                if len(all_names) == len(row):
                    dicts.append(dict(zip(all_names, row)))
                else:
                    dicts.append(dict(zip(field_names, row)))
        
        return dicts
    
    async def aall(self) -> list[dict[str, Any]]:
        """Async version of all()."""
        return self.all()
    
    def __iter__(self):
        return iter(self.all())
    
    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        for item in self.all():
            yield item
    
    def using(self, session: Session) -> "ValuesQuerySet[T]":
        """Use a specific session."""
        clone = self._clone()
        clone._session = session
        return clone


class ValuesListQuerySet(Generic[T]):
    """
    QuerySet that returns tuples instead of models.
    """
    
    def __init__(
        self,
        model: type[T],
        session: Session | None = None,
        *,
        fields: list[str] | None = None,
        flat: bool = False,
        filters: list[ColumnElement[bool]] | None = None,
        excludes: list[ColumnElement[bool]] | None = None,
        order_by: list[Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        annotations: list[Annotation] | None = None,
        group_by_fields: list[str] | None = None,
        distinct: bool = False,
    ):
        self.model = model
        self._session = session
        self._fields = fields or []
        self._flat = flat
        self._filters = filters or []
        self._excludes = excludes or []
        self._order_by = order_by or []
        self._limit = limit
        self._offset = offset
        self._annotations = annotations or []
        self._group_by_fields = group_by_fields or []
        self._distinct = distinct
        
        if flat and len(self._fields) != 1:
            raise ValueError("'flat' requires exactly one field")
    
    def _clone(self, **kwargs: Any) -> "ValuesListQuerySet[T]":
        """Clone this ValuesListQuerySet."""
        return ValuesListQuerySet(
            self.model,
            self._session,
            fields=kwargs.get('fields', self._fields.copy()),
            flat=kwargs.get('flat', self._flat),
            filters=kwargs.get('filters', self._filters.copy()),
            excludes=kwargs.get('excludes', self._excludes.copy()),
            order_by=kwargs.get('order_by', self._order_by.copy()),
            limit=kwargs.get('limit', self._limit),
            offset=kwargs.get('offset', self._offset),
            annotations=kwargs.get('annotations', self._annotations.copy()),
            group_by_fields=kwargs.get('group_by_fields', self._group_by_fields.copy()),
            distinct=kwargs.get('distinct', self._distinct),
        )
    
    def filter(self, *args: Q | ColumnElement[bool], **kwargs: Any) -> "ValuesListQuerySet[T]":
        """Add filter conditions."""
        clone = self._clone()
        for arg in args:
            if isinstance(arg, Q):
                condition = arg.to_where_clause(self.model)
                if condition is not None:
                    clone._filters.append(condition)
            else:
                clone._filters.append(arg)
        for key, value in kwargs.items():
            q = Q(**{key: value})
            condition = q.to_where_clause(self.model)
            if condition is not None:
                clone._filters.append(condition)
        return clone
    
    def annotate(
        self, 
        *args: Annotation | Aggregate,
        **kwargs: Annotation | Aggregate
    ) -> "ValuesListQuerySet[T]":
        """Add annotations."""
        clone = self._clone(flat=False)  # Can't be flat with annotations
        for annotation in args:
            if isinstance(annotation, Aggregate):
                clone._annotations.append(Annotation(annotation))
            else:
                clone._annotations.append(annotation)
        for alias, annotation in kwargs.items():
            if isinstance(annotation, Aggregate):
                clone._annotations.append(Annotation(annotation, alias=alias))
            else:
                annotation.alias = alias
                clone._annotations.append(annotation)
        return clone
    
    def _build_statement(self) -> Select:
        """Build the SQLAlchemy select statement."""
        if self._fields:
            columns = [
                getattr(self.model, f) 
                for f in self._fields 
                if hasattr(self.model, f)
            ]
        else:
            columns = [self.model]
        
        statement = select(*columns)
        
        # Add annotations
        for annotation in self._annotations:
            statement = statement.add_columns(
                annotation.to_sqlalchemy(self.model)
            )
        
        # Apply filters
        for f in self._filters:
            statement = statement.where(f)
        for f in self._excludes:
            statement = statement.where(f)
        
        # GROUP BY
        group_fields = self._group_by_fields or self._fields
        if group_fields:
            for field in group_fields:
                if hasattr(self.model, field):
                    statement = statement.group_by(getattr(self.model, field))
        
        # Apply ordering
        for order in self._order_by:
            statement = statement.order_by(order)
        
        # Apply limit/offset
        if self._limit is not None:
            statement = statement.limit(self._limit)
        if self._offset is not None:
            statement = statement.offset(self._offset)
        
        # Apply distinct
        if self._distinct:
            statement = statement.distinct()
        
        return statement
    
    def all(self) -> list[tuple[Any, ...]] | list[Any]:
        """Get all results as tuples or flat list."""
        if not self._session:
            raise RuntimeError("No session available.")
        
        statement = self._build_statement()
        results = self._session.exec(statement).all()
        
        if self._flat:
            # Return flat list
            return [row[0] if isinstance(row, tuple) else row for row in results]
        
        return list(results)
    
    async def aall(self) -> list[tuple[Any, ...]] | list[Any]:
        """Async version of all()."""
        return self.all()
    
    def __iter__(self):
        return iter(self.all())
    
    async def __aiter__(self) -> AsyncIterator[Any]:
        for item in self.all():
            yield item
    
    def using(self, session: Session) -> "ValuesListQuerySet[T]":
        """Use a specific session."""
        clone = self._clone()
        clone._session = session
        return clone


# =============================================================================
# Model Manager Mixin
# =============================================================================

class QuerySetManager:
    """
    Manager for creating QuerySets from model classes.
    
    This is typically added to a model class as the 'objects' attribute.
    
    Example:
        class Book(BaseModel, table=True):
            title: str
            price: float
            
            objects = QuerySetManager()
    """
    
    def __init__(self, model: type[SQLModel] | None = None):
        self.model = model
    
    def __get__(self, instance: Any, owner: type[SQLModel]) -> "QuerySetManager":
        if self.model is None:
            self.model = owner
        return self
    
    def all(self) -> QuerySet:
        """Get a QuerySet for all records."""
        return QuerySet(self.model)
    
    def filter(self, *args, **kwargs) -> QuerySet:
        """Create a filtered QuerySet."""
        return QuerySet(self.model).filter(*args, **kwargs)
    
    def exclude(self, *args, **kwargs) -> QuerySet:
        """Create an excluded QuerySet."""
        return QuerySet(self.model).exclude(*args, **kwargs)
    
    def get(self, session: Session, **kwargs) -> SQLModel | None:
        """Get a single record by filters."""
        return QuerySet(self.model).using(session).filter(**kwargs).first()
    
    async def aget(self, **kwargs) -> SQLModel | None:
        """Async get a single record."""
        return await QuerySet(self.model).filter(**kwargs).afirst()
    
    def create(self, session: Session, **kwargs) -> SQLModel:
        """Create a new record."""
        instance = self.model(**kwargs)
        session.add(instance)
        session.commit()
        session.refresh(instance)
        return instance
    
    async def acreate(self, **kwargs) -> SQLModel:
        """Async create a new record."""
        # Would use async session in production
        raise NotImplementedError("Async create requires async session")
    
    def aggregate(self, *args, **kwargs) -> dict[str, Any]:
        """Run aggregation without session (requires session context)."""
        return QuerySet(self.model).aggregate(*args, **kwargs)
    
    def annotate(self, *args, **kwargs) -> QuerySet:
        """Create an annotated QuerySet."""
        return QuerySet(self.model).annotate(*args, **kwargs)
    
    def values(self, *fields) -> ValuesQuerySet:
        """Create a values QuerySet."""
        return QuerySet(self.model).values(*fields)
    
    def values_list(self, *fields, flat: bool = False) -> ValuesListQuerySet:
        """Create a values_list QuerySet."""
        return QuerySet(self.model).values_list(*fields, flat=flat)
    
    def count(self, session: Session, **filters) -> int:
        """Count records matching filters."""
        return QuerySet(self.model).using(session).filter(**filters).count()
    
    def exists(self, session: Session, **filters) -> bool:
        """Check if records exist matching filters."""
        return QuerySet(self.model).using(session).filter(**filters).exists()
    
    def using(self, session: Session) -> QuerySet:
        """Create a QuerySet with a specific session."""
        return QuerySet(self.model).using(session)
