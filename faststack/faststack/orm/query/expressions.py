"""
SQL Expressions: Case, When, Value, Subquery, Exists, RawSQL.

Provides building blocks for complex SQL expressions.

Example:
    from faststack.orm.query import Case, When, Value

    # Conditional annotation
    await User.annotate(
        status_text=Case(
            When(age__lt=18, then=Value('minor')),
            When(age__gte=18, age__lt=65, then=Value('adult')),
            default=Value('senior'),
        )
    )
"""

from typing import Any, List, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from .q import Q, Connector

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement, Select


@dataclass
class Value:
    """
    Literal value wrapper for use in expressions.

    Example:
        Value(42)
        Value('hello')
        Value(None)
    """

    value: Any

    def __repr__(self) -> str:
        return f"Value({self.value!r})"

    def to_sqlalchemy(self, model: type = None) -> 'ColumnElement':
        """Convert to SQLAlchemy literal."""
        from sqlalchemy import literal
        return literal(self.value)


@dataclass
class When:
    """
    Condition clause for Case expressions.

    Example:
        When(age__lt=18, then=Value('minor'))
        When(Q(status='active') & Q(verified=True), then=F('bonus'))
    """

    # Condition (Q object or kwargs for automatic Q construction)
    condition: Optional[Q] = None

    # Result value when condition is true
    result: Any = None

    def __init__(
        self,
        *args: Q,
        condition: Optional[Q] = None,
        then: Any = None,
        **kwargs: Any
    ):
        """
        Initialize When clause.

        Args:
            *args: Q objects to combine as condition
            condition: Explicit Q condition
            then: Result value when condition is true
            **kwargs: Field lookups for automatic Q construction
        """
        # Build condition from args and kwargs
        conditions = list(args)

        if condition:
            conditions.append(condition)

        if kwargs:
            conditions.append(Q(**kwargs))

        # Combine all conditions with AND
        if not conditions:
            self.condition = Q()
        elif len(conditions) == 1:
            self.condition = conditions[0]
        else:
            result = conditions[0]
            for c in conditions[1:]:
                result = result & c
            self.condition = result

        self.result = then

    def __repr__(self) -> str:
        return f"When({self.condition!r}, then={self.result!r})"

    def to_sqlalchemy(self, model: type) -> tuple:
        """
        Convert to SQLAlchemy case tuple.

        Returns:
            Tuple of (condition_expression, result_expression)
        """
        cond_expr = self.condition.to_sqlalchemy(model)

        if isinstance(self.result, (F, Value, Case)):
            result_expr = self.result.to_sqlalchemy(model)
        else:
            from sqlalchemy import literal
            result_expr = literal(self.result)

        return (cond_expr, result_expr)


@dataclass
class Case:
    """
    SQL CASE expression for conditional logic.

    Example:
        Case(
            When(age__lt=18, then=Value('minor')),
            When(age__lt=65, then=Value('adult')),
            default=Value('senior')
        )
    """

    # When clauses
    cases: List[When] = field(default_factory=list)

    # Default value if no condition matches
    default: Any = None

    def __init__(self, *cases: When, default: Any = None):
        """
        Initialize Case expression.

        Args:
            *cases: When clauses
            default: Default value if no condition matches
        """
        self.cases = list(cases)
        self.default = default

    def __repr__(self) -> str:
        cases_str = ", ".join(repr(c) for c in self.cases)
        return f"Case({cases_str}, default={self.default!r})"

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        """Convert to SQLAlchemy case expression."""
        from sqlalchemy import case, literal

        # Build whens list
        whens = [c.to_sqlalchemy(model) for c in self.cases]

        # Build default
        if self.default is not None:
            if isinstance(self.default, (F, Value, Case)):
                default_expr = self.default.to_sqlalchemy(model)
            else:
                default_expr = literal(self.default)
        else:
            default_expr = None

        # Build case expression
        # SQLAlchemy case format: case((condition, result), ..., else_=default)
        return case(*whens, else_=default_expr)


@dataclass
class RawSQL:
    """
    Raw SQL expression for database-specific features.

    WARNING: RawSQL bypasses ORM abstraction. Use with caution.

    Example:
        RawSQL('RANDOM()')
        RawSQL('EXTRACT(EPOCH FROM created_at)')
        RawSQL('price * %s', [1.1])  # With params
    """

    sql: str
    params: Optional[list] = None

    def __init__(self, sql: str, params: Optional[list] = None):
        self.sql = sql
        self.params = params or []

    def __repr__(self) -> str:
        return f"RawSQL('{self.sql}')"

    def to_sqlalchemy(self, model: type = None) -> 'ColumnElement':
        """Convert to SQLAlchemy text expression."""
        from sqlalchemy import text
        if self.params:
            return text(self.sql).bindparams(*self.params)
        return text(self.sql)


class Subquery:
    """
    Subquery expression for correlated queries.

    Example:
        # Count related objects
        comment_count = Subquery(
            Comment.filter(post_id=OuterRef('id'))
            .annotate(count=Count('id'))
            .values('count')
        )

        await Post.annotate(comment_count=comment_count)
    """

    def __init__(self, query: 'Select', output_field: Any = None):
        """
        Initialize subquery.

        Args:
            query: SQLAlchemy select query
            output_field: Expected output field type
        """
        self.query = query
        self.output_field = output_field

    def __repr__(self) -> str:
        return f"Subquery({self.query!r})"

    def to_sqlalchemy(self, model: type = None) -> 'ColumnElement':
        """Return the subquery."""
        return self.query.scalar_subquery()


class OuterRef:
    """
    Reference to outer query field in subqueries.

    Example:
        Subquery(
            Comment.filter(post_id=OuterRef('id'))
            .annotate(count=Count('id'))
            .values('count')
        )
    """

    def __init__(self, field: str):
        self.field = field

    def __repr__(self) -> str:
        return f"OuterRef('{self.field}')"

    def to_sqlalchemy(self, model: type = None) -> 'ColumnElement':
        """This is handled specially in the query builder."""
        raise NotImplementedError("OuterRef must be resolved in the context of a subquery")


class Exists:
    """
    EXISTS subquery expression.

    Example:
        # Filter posts that have comments
        await Post.filter(
            Exists(Comment.filter(post_id=OuterRef('id')))
        )
    """

    def __init__(self, query: 'Select', negated: bool = False):
        """
        Initialize EXISTS expression.

        Args:
            query: Subquery to check for existence
            negated: If True, use NOT EXISTS
        """
        self.query = query
        self.negated = negated

    def __repr__(self) -> str:
        return f"{'Not' if self.negated else ''}Exists({self.query!r})"

    def __invert__(self) -> 'Exists':
        """Negate the EXISTS (becomes NOT EXISTS)."""
        return Exists(self.query, negated=not self.negated)

    def to_sqlalchemy(self, model: type = None) -> 'ColumnElement':
        """Convert to SQLAlchemy exists expression."""
        from sqlalchemy import exists, not_

        expr = exists(self.query)

        if self.negated:
            return not_(expr)

        return expr


# Import F after class definitions to avoid circular import
from .f import F
