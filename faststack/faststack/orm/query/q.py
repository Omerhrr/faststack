"""
Q Objects for complex database queries.

Provides AND, OR, NOT operations for building complex filter conditions.

Example:
    from faststack.orm.query import Q

    # AND (default)
    Q(name='John', age=25)  # name='John' AND age=25

    # OR
    Q(name='John') | Q(name='Jane')  # name='John' OR name='Jane'

    # NOT
    ~Q(name='John')  # NOT name='John'

    # Complex combinations
    Q(name='John') | (Q(age__gte=25) & Q(status='active'))
"""

from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import copy

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement


class Connector(Enum):
    """Logical connectors for combining Q objects."""
    AND = "AND"
    OR = "OR"


@dataclass
class QNode:
    """
    Base node for Q object tree.

    Q objects can be combined to form a tree structure representing
    complex boolean logic for database queries.
    """
    pass


@dataclass
class Q(QNode):
    """
    Q object for encapsulating filter conditions.

    Supports:
    - Simple lookups: Q(name='John')
    - Field lookups: Q(age__gte=25), Q(name__contains='oh')
    - Negation: ~Q(name='John')
    - Combination: Q(...) & Q(...), Q(...) | Q(...)

    Example:
        # Simple filter
        Q(name='John')

        # Field lookups
        Q(age__gte=25)
        Q(name__icontains='john')
        Q(created_at__year=2024)

        # Negation
        ~Q(is_deleted=True)

        # Combination
        Q(status='active') & Q(age__gte=25)
        Q(name='John') | Q(name='Jane')
    """

    # Children nodes (for combined Q objects)
    children: List[Tuple[Union['Q', str], Any]] = field(default_factory=list)

    # Logical connector
    connector: Connector = Connector.AND

    # Whether this node is negated
    negated: bool = False

    def __init__(
        self,
        *args: 'Q',
        _connector: Connector = Connector.AND,
        _negated: bool = False,
        **kwargs: Any
    ):
        """
        Initialize Q object.

        Args:
            *args: Child Q objects
            _connector: AND or OR connector
            _negated: Whether to negate the entire condition
            **kwargs: Field lookups (field__lookup=value)
        """
        self.children = []
        self.connector = _connector
        self.negated = _negated

        # Add positional Q objects as children
        for q in args:
            if isinstance(q, Q):
                self.children.append((q, None))
            else:
                raise TypeError(f"Expected Q object, got {type(q)}")

        # Add keyword arguments as field lookups
        for key, value in kwargs.items():
            self.children.append((key, value))

    def __and__(self, other: 'Q') -> 'Q':
        """Combine with another Q object using AND."""
        if not isinstance(other, Q):
            raise TypeError(f"Cannot combine Q with {type(other)}")

        if self.connector == Connector.AND and not self.negated:
            # Optimize: merge into existing AND node
            result = Q(_connector=Connector.AND)
            result.children = list(self.children)
            if other.connector == Connector.AND and not other.negated:
                result.children.extend(other.children)
            else:
                result.children.append((other, None))
            return result

        return Q(self, other, _connector=Connector.AND)

    def __or__(self, other: 'Q') -> 'Q':
        """Combine with another Q object using OR."""
        if not isinstance(other, Q):
            raise TypeError(f"Cannot combine Q with {type(other)}")

        if self.connector == Connector.OR and not self.negated:
            result = Q(_connector=Connector.OR)
            result.children = list(self.children)
            if other.connector == Connector.OR and not other.negated:
                result.children.extend(other.children)
            else:
                result.children.append((other, None))
            return result

        return Q(self, other, _connector=Connector.OR)

    def __invert__(self) -> 'Q':
        """Negate this Q object using ~ operator."""
        result = Q(_connector=self.connector, _negated=not self.negated)
        result.children = list(self.children)
        return result

    def __repr__(self) -> str:
        """String representation."""
        if self.children:
            children_repr = []
            for child, value in self.children:
                if isinstance(child, Q):
                    children_repr.append(repr(child))
                else:
                    children_repr.append(f"{child}={repr(value)}")
            op = f" {self.connector.value} "
            result = op.join(children_repr)
            if len(self.children) > 1:
                result = f"({result})"
        else:
            result = "Q()"

        if self.negated:
            result = f"~{result}"
        return result

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, Q):
            return False
        return (
            self.children == other.children
            and self.connector == other.connector
            and self.negated == other.negated
        )

    def __hash__(self) -> int:
        """Make Q object hashable."""
        return hash((tuple(self.children), self.connector, self.negated))

    def copy(self) -> 'Q':
        """Create a deep copy of this Q object."""
        result = Q(_connector=self.connector, _negated=self.negated)
        result.children = [
            (child.copy() if isinstance(child, Q) else child, value)
            for child, value in self.children
        ]
        return result

    def add(self, other: 'Q', connector: Connector = Connector.AND) -> 'Q':
        """
        Add another Q object with specified connector.

        Args:
            other: Q object to add
            connector: AND or OR connector

        Returns:
            Combined Q object
        """
        if connector == Connector.AND:
            return self & other
        return self | other

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        """
        Convert Q object to SQLAlchemy expression.

        Args:
            model: SQLAlchemy model class

        Returns:
            SQLAlchemy ColumnElement expression
        """
        from sqlalchemy import and_, or_, not_, select
        from sqlalchemy.sql import expression

        expressions = []

        for child, value in self.children:
            if isinstance(child, Q):
                # Recursive: convert nested Q object
                expr = child.to_sqlalchemy(model)
            else:
                # Field lookup
                expr = self._build_lookup(model, child, value)

            expressions.append(expr)

        # Combine expressions based on connector
        if not expressions:
            result = expression.true()
        elif self.connector == Connector.AND:
            result = and_(*expressions)
        else:
            result = or_(*expressions)

        # Apply negation
        if self.negated:
            result = not_(result)

        return result

    def _build_lookup(self, model: type, field_lookup: str, value: Any) -> 'ColumnElement':
        """
        Build SQLAlchemy expression for a field lookup.

        Args:
            model: SQLAlchemy model class
            field_lookup: Field name with optional lookup suffix (e.g., 'name__icontains')
            value: Lookup value

        Returns:
            SQLAlchemy expression
        """
        from sqlalchemy import not_, any_, all_
        from sqlalchemy.sql import expression

        # Parse field and lookup
        parts = field_lookup.split('__')
        field_name = parts[0]
        lookup = parts[1] if len(parts) > 1 else 'exact'

        # Get column
        if not hasattr(model, field_name):
            raise AttributeError(f"Model {model.__name__} has no field '{field_name}'")

        column = getattr(model, field_name)

        # Handle relationship traversing (e.g., 'author__name')
        if len(parts) > 2:
            # For now, handle simple relationships
            # This would need to be expanded for deep traversing
            lookup = parts[-1]

        # Build expression based on lookup type
        if lookup == 'exact':
            return column == value
        elif lookup == 'iexact':
            return column.ilike(value)
        elif lookup == 'contains':
            return column.contains(value)
        elif lookup == 'icontains':
            return column.ilike(f'%{value}%')
        elif lookup == 'startswith':
            return column.startswith(value)
        elif lookup == 'istartswith':
            return column.ilike(f'{value}%')
        elif lookup == 'endswith':
            return column.endswith(value)
        elif lookup == 'iendswith':
            return column.ilike(f'%{value}')
        elif lookup == 'gt':
            return column > value
        elif lookup == 'gte':
            return column >= value
        elif lookup == 'lt':
            return column < value
        elif lookup == 'lte':
            return column <= value
        elif lookup == 'in':
            return column.in_(value)
        elif lookup == 'isnull':
            return column.is_(None) if value else column.isnot(None)
        elif lookup == 'regex':
            return column.op('~')(value)
        elif lookup == 'iregex':
            return column.op('~*')(value)
        elif lookup == 'range':
            return column.between(value[0], value[1])
        elif lookup == 'year':
            return expression.extract('year', column) == value
        elif lookup == 'month':
            return expression.extract('month', column) == value
        elif lookup == 'day':
            return expression.extract('day', column) == value
        elif lookup == 'week_day':
            return expression.extract('dow', column) == value
        elif lookup == 'hour':
            return expression.extract('hour', column) == value
        elif lookup == 'minute':
            return expression.extract('minute', column) == value
        elif lookup == 'second':
            return expression.extract('second', column) == value
        else:
            raise ValueError(f"Unknown lookup: {lookup}")


def q_combine(conector: Connector, *q_objects: Q) -> Q:
    """
    Combine multiple Q objects.

    Args:
        connector: AND or OR
        *q_objects: Q objects to combine

    Returns:
        Combined Q object
    """
    if not q_objects:
        return Q()

    result = q_objects[0]
    for q in q_objects[1:]:
        result = result.add(q, conector)

    return result


def q_and(*q_objects: Q) -> Q:
    """Combine Q objects with AND."""
    return q_combine(Connector.AND, *q_objects)


def q_or(*q_objects: Q) -> Q:
    """Combine Q objects with OR."""
    return q_combine(Connector.OR, *q_objects)
