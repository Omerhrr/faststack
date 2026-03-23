"""
FastStack ORM Expressions

Provides Q objects, F expressions, and related expression classes for
building complex database queries. Django-compatible but async-first.

Features:
- Q objects for complex AND/OR/NOT queries
- F expressions for field references in queries
- Value wrapper for expression values
- ExpressionWrapper for type expressions
- RawSQL for raw SQL fragments
- Case/When for conditional expressions
- Exists/Subquery for subquery expressions

Example:
    >>> from faststack.orm.expressions import Q, F
    >>> 
    >>> # Q objects
    >>> Q(name='John') | Q(name='Jane')
    >>> Q(age__gt=18) & Q(is_active=True)
    >>> ~Q(name__startswith='Admin')
    >>> 
    >>> # F expressions
    >>> Product.objects.update(price=F('price') * 1.1)
    >>> Product.filter(stock__gt=F('min_stock'))
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, TYPE_CHECKING

from faststack.orm.query_utils import Node, Connector

if TYPE_CHECKING:
    from faststack.orm.base import BaseModel


class Expression(ABC):
    """
    Base class for all SQL expressions.
    
    Abstract base that provides common interface for all expression types.
    """
    
    @abstractmethod
    def as_sql(self) -> tuple[str, list[Any]]:
        """
        Generate SQL representation.
        
        Returns:
            Tuple of (sql_string, params_list)
        """
        pass
    
    @property
    def contains_aggregate(self) -> bool:
        """Whether this expression contains an aggregate function."""
        return False
    
    def get_source_expressions(self) -> list["Expression"]:
        """Return source expressions for this expression."""
        return []
    
    def set_source_expressions(self, exprs: list["Expression"]) -> None:
        """Set source expressions for this expression."""
        pass
    
    def resolve_expression(
        self,
        query: Any = None,
        allow_joins: bool = True,
        reuse: Any = None,
        summarize: bool = False,
    ) -> "Expression":
        """
        Resolve the expression in the context of a query.
        
        Args:
            query: The query being built
            allow_joins: Whether joins are allowed
            reuse: Reuse existing joins
            summarize: Whether this is for summary queries
        
        Returns:
            Resolved expression
        """
        return self
    
    def copy(self) -> "Expression":
        """Create a copy of this expression."""
        return self.__class__.__new__(self.__class__)


class Combinable:
    """
    Mixin for expressions that can be combined with arithmetic operators.
    
    Provides __add__, __sub__, __mul__, __truediv__, __mod__ and their
    reverse versions for building arithmetic expressions.
    """
    
    def _combine(self, other: Any, operator: str, reversed: bool = False) -> "CombinedExpression":
        """
        Combine this expression with another using an operator.
        
        Args:
            other: The other operand
            operator: The arithmetic operator (+, -, *, /, %)
            reversed: If True, operands are reversed (for __radd__ etc.)
        
        Returns:
            CombinedExpression with the operation
        """
        if not isinstance(other, Expression):
            other = Value(other)
        
        if reversed:
            return CombinedExpression(other, operator, self)
        return CombinedExpression(self, operator, other)
    
    def __add__(self, other: Any) -> "CombinedExpression":
        """Add operation: F('price') + 10"""
        return self._combine(other, "+")
    
    def __radd__(self, other: Any) -> "CombinedExpression":
        """Reverse add operation: 10 + F('price')"""
        return self._combine(other, "+", reversed=True)
    
    def __sub__(self, other: Any) -> "CombinedExpression":
        """Subtract operation: F('stock') - 1"""
        return self._combine(other, "-")
    
    def __rsub__(self, other: Any) -> "CombinedExpression":
        """Reverse subtract operation: 100 - F('discount')"""
        return self._combine(other, "-", reversed=True)
    
    def __mul__(self, other: Any) -> "CombinedExpression":
        """Multiply operation: F('price') * 1.1"""
        return self._combine(other, "*")
    
    def __rmul__(self, other: Any) -> "CombinedExpression":
        """Reverse multiply operation: 1.1 * F('price')"""
        return self._combine(other, "*", reversed=True)
    
    def __truediv__(self, other: Any) -> "CombinedExpression":
        """Divide operation: F('total') / F('count')"""
        return self._combine(other, "/")
    
    def __rtruediv__(self, other: Any) -> "CombinedExpression":
        """Reverse divide operation: 100 / F('percent')"""
        return self._combine(other, "/", reversed=True)
    
    def __mod__(self, other: Any) -> "CombinedExpression":
        """Modulo operation: F('id') % 10"""
        return self._combine(other, "%")
    
    def __rmod__(self, other: Any) -> "CombinedExpression":
        """Reverse modulo operation: 100 % F('divisor')"""
        return self._combine(other, "%", reversed=True)
    
    def __pow__(self, other: Any) -> "CombinedExpression":
        """Power operation: F('base') ** 2"""
        return self._combine(other, "^")
    
    def __rpow__(self, other: Any) -> "CombinedExpression":
        """Reverse power operation: 2 ** F('exponent')"""
        return self._combine(other, "^", reversed=True)
    
    def __neg__(self) -> "CombinedExpression":
        """Negation operation: -F('value')"""
        return CombinedExpression(Value(0), "-", self)
    
    def __pos__(self) -> "CombinedExpression":
        """Positive operation: +F('value')"""
        return self  # type: ignore
    
    def __abs__(self) -> "CombinedExpression":
        """Absolute value: abs(F('value'))"""
        return Func("ABS", [self])
    
    # Comparison operators - return Q-like objects for filter usage
    def __eq__(self, other: Any) -> Any:  # type: ignore
        """Equality comparison: F('field') == value"""
        if isinstance(other, Expression):
            return ExpressionCondition(self, "=", other)
        return super().__eq__(other)
    
    def __ne__(self, other: Any) -> Any:  # type: ignore
        """Inequality comparison: F('field') != value"""
        if isinstance(other, Expression):
            return ExpressionCondition(self, "!=", other)
        return super().__ne__(other)
    
    def __lt__(self, other: Any) -> "ExpressionCondition":
        """Less than: F('created_at') < F('updated_at')"""
        if not isinstance(other, Expression):
            other = Value(other)
        return ExpressionCondition(self, "<", other)
    
    def __le__(self, other: Any) -> "ExpressionCondition":
        """Less than or equal: F('age') <= 65"""
        if not isinstance(other, Expression):
            other = Value(other)
        return ExpressionCondition(self, "<=", other)
    
    def __gt__(self, other: Any) -> "ExpressionCondition":
        """Greater than: F('age') > 18"""
        if not isinstance(other, Expression):
            other = Value(other)
        return ExpressionCondition(self, ">", other)
    
    def __ge__(self, other: Any) -> "ExpressionCondition":
        """Greater than or equal: F('stock') >= 0"""
        if not isinstance(other, Expression):
            other = Value(other)
        return ExpressionCondition(self, ">=", other)


class CombinedExpression(Expression, Combinable):
    """
    Expression representing a combination of two expressions with an operator.
    
    Created when using arithmetic operators on expressions.
    
    Example:
        >>> expr = F('price') * 1.1
        >>> expr.as_sql()
        ('"price" * %s', [1.1])
    """
    
    def __init__(self, lhs: Expression, operator: str, rhs: Expression) -> None:
        self.lhs = lhs
        self.operator = operator
        self.rhs = rhs
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """Generate SQL for the combined expression."""
        lhs_sql, lhs_params = self.lhs.as_sql()
        rhs_sql, rhs_params = self.rhs.as_sql()
        
        sql = f"({lhs_sql} {self.operator} {rhs_sql})"
        return sql, lhs_params + rhs_params
    
    def get_source_expressions(self) -> list[Expression]:
        return [self.lhs, self.rhs]
    
    def set_source_expressions(self, exprs: list[Expression]) -> None:
        if len(exprs) == 2:
            self.lhs, self.rhs = exprs
    
    def __repr__(self) -> str:
        return f"CombinedExpression({self.lhs!r}, {self.operator!r}, {self.rhs!r})"
    
    def copy(self) -> "CombinedExpression":
        return CombinedExpression(
            self.lhs.copy(),
            self.operator,
            self.rhs.copy(),
        )


class ExpressionCondition:
    """
    Condition created from expression comparisons.
    
    Used for filtering with expression comparisons like:
    F('created_at') < F('updated_at')
    
    Can be combined with Q objects.
    """
    
    def __init__(self, lhs: Expression, operator: str, rhs: Expression) -> None:
        self.lhs = lhs
        self.operator = operator
        self.rhs = rhs
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """Generate SQL for the condition."""
        lhs_sql, lhs_params = self.lhs.as_sql()
        rhs_sql, rhs_params = self.rhs.as_sql()
        
        sql = f"{lhs_sql} {self.operator} {rhs_sql}"
        return sql, lhs_params + rhs_params
    
    def __repr__(self) -> str:
        return f"ExpressionCondition({self.lhs!r} {self.operator} {self.rhs!r})"
    
    def __and__(self, other: Any) -> "Q":
        """Combine with another condition using AND."""
        q = Q(_condition=self)
        return q & other
    
    def __or__(self, other: Any) -> "Q":
        """Combine with another condition using OR."""
        q = Q(_condition=self)
        return q | other
    
    def __invert__(self) -> "Q":
        """Negate the condition."""
        return ~Q(_condition=self)


class F(Expression, Combinable):
    """
    Expression representing the value of a model field.
    
    Used to reference model fields in queries without fetching them first.
    Useful for:
    - Atomic updates: `Model.objects.update(count=F('count') + 1)`
    - Comparisons: `Model.filter(created_at__lt=F('updated_at'))`
    - Annotations: `Model.annotate(full_name=F('first_name') + ' ' + F('last_name'))`
    
    Example:
        >>> F('price')
        F('price')
        
        >>> F('price') * 1.1  # Increase price by 10%
        CombinedExpression(F('price'), '*', Value(1.1))
        
        >>> Product.filter(price__gt=F('base_price'))
        # WHERE price > base_price
    """
    
    def __init__(self, name: str) -> None:
        """
        Initialize an F expression.
        
        Args:
            name: The field name to reference
        """
        self.name = name
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """Generate SQL for the field reference."""
        # Quote the field name to avoid SQL injection
        return f'"{self.name}"', []
    
    def __repr__(self) -> str:
        return f"F({self.name!r})"
    
    def __eq__(self, other: Any) -> Any:  # type: ignore
        """Check equality with another expression."""
        if isinstance(other, F):
            return self.name == other.name
        return super().__eq__(other)
    
    def __hash__(self) -> int:
        return hash(self.name)
    
    def copy(self) -> "F":
        return F(self.name)


class Q(Node, Expression):
    """
    Expression for building complex queries with AND, OR, and NOT logic.
    
    Q objects can be combined using:
    - `&` (AND): `Q(name='John') & Q(age__gt=18)`
    - `|` (OR): `Q(name='John') | Q(name='Jane')`
    - `~` (NOT): `~Q(name='Admin')`
    
    Example:
        >>> # Simple condition
        >>> Q(name='John')
        <Q: {'name': 'John'}>
        
        >>> # Complex condition
        >>> (Q(name='John') | Q(name='Jane')) & Q(age__gt=18)
        <Q: (OR(name='John', name='Jane') AND age__gt=18)>
        
        >>> # Negation
        >>> ~Q(name__startswith='Admin')
        <Q: NOT name__startswith='Admin'>
        
        >>> # Nested Q objects
        >>> Q(Q(name='John') | Q(name='Jane'), age__gt=18)
    """
    
    def __init__(
        self,
        *args: Any,
        _connector: Connector = Connector.AND,
        _negated: bool = False,
        _condition: ExpressionCondition | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a Q object.
        
        Args:
            *args: Positional Q objects or dicts to combine
            _connector: How to combine conditions (AND/OR)
            _negated: Whether to negate this Q object
            _condition: An ExpressionCondition to wrap
            **kwargs: Field lookups (name='John', age__gt=18)
        """
        super().__init__(
            *args,
            connector=_connector,
            negated=_negated,
            **kwargs,
        )
        self._condition = _condition
    
    @property
    def _connector(self) -> Connector:
        """Get the connector (for Django compatibility)."""
        return self.connector
    
    @_connector.setter
    def _connector(self, value: Connector) -> None:
        """Set the connector (for Django compatibility)."""
        self.connector = value
    
    @property
    def _negated(self) -> bool:
        """Get whether negated (for Django compatibility)."""
        return self.negated
    
    @_negated.setter
    def _negated(self, value: bool) -> None:
        """Set whether negated (for Django compatibility)."""
        self.negated = value
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """
        Generate SQL for this Q object.
        
        Returns:
            Tuple of (sql_string, params_list)
        """
        if self._condition:
            return self._condition.as_sql()
        
        parts: list[str] = []
        params: list[Any] = []
        
        for child in self.children:
            if isinstance(child, Q):
                child_sql, child_params = child.as_sql()
                if child_sql:
                    parts.append(f"({child_sql})")
                    params.extend(child_params)
            elif isinstance(child, ExpressionCondition):
                child_sql, child_params = child.as_sql()
                parts.append(child_sql)
                params.extend(child_params)
            elif isinstance(child, tuple):
                key, value = child
                sql, child_params = self._build_lookup_sql(key, value)
                parts.append(sql)
                params.extend(child_params)
        
        connector_sql = " AND " if self._connector == Connector.AND else " OR "
        sql = connector_sql.join(parts)
        
        if self._negated and sql:
            sql = f"NOT ({sql})"
        
        return sql, params
    
    def _build_lookup_sql(self, key: str, value: Any) -> tuple[str, list[Any]]:
        """Build SQL for a field lookup."""
        # Parse the lookup
        from faststack.orm.query_utils import parse_lookup
        
        lookup_info = parse_lookup(key, value)
        field = lookup_info.field_name
        lookup = lookup_info.lookup
        val = lookup_info.value
        
        # Build SQL based on lookup type
        if lookup == "exact":
            if val is None:
                return f'"{field}" IS NULL', []
            return f'"{field}" = ?', [val]
        elif lookup == "iexact":
            if val is None:
                return f'"{field}" IS NULL', []
            return f'LOWER("{field}") = LOWER(?)', [val]
        elif lookup == "contains":
            return f'"{field}" LIKE ?', [f"%{val}%"]
        elif lookup == "icontains":
            return f'LOWER("{field}") LIKE LOWER(?)', [f"%{val}%"]
        elif lookup == "startswith":
            return f'"{field}" LIKE ?', [f"{val}%"]
        elif lookup == "istartswith":
            return f'LOWER("{field}") LIKE LOWER(?)', [f"{val}%"]
        elif lookup == "endswith":
            return f'"{field}" LIKE ?', [f"%{val}"]
        elif lookup == "iendswith":
            return f'LOWER("{field}") LIKE LOWER(?)', [f"%{val}"]
        elif lookup == "gt":
            return f'"{field}" > ?', [val]
        elif lookup == "gte":
            return f'"{field}" >= ?', [val]
        elif lookup == "lt":
            return f'"{field}" < ?', [val]
        elif lookup == "lte":
            return f'"{field}" <= ?', [val]
        elif lookup == "in":
            if isinstance(val, (list, tuple)) and len(val) > 0:
                placeholders = ", ".join(["?"] * len(val))
                return f'"{field}" IN ({placeholders})', list(val)
            return '"{field}" IN (?)', [val]
        elif lookup == "isnull":
            if val:
                return f'"{field}" IS NULL', []
            return f'"{field}" IS NOT NULL', []
        elif lookup == "regex":
            return f'"{field}" REGEXP ?', [val]
        elif lookup == "iregex":
            return f'"{field}" REGEXP ?', [val]  # Case varies by DB
        elif lookup == "range":
            if isinstance(val, (list, tuple)) and len(val) == 2:
                return f'"{field}" BETWEEN ? AND ?', list(val)
            raise ValueError("range lookup requires a 2-element list/tuple")
        else:
            # Default to exact match
            return f'"{field}" = ?', [val]
    
    def __repr__(self) -> str:
        if self._condition:
            return f"<Q: {self._condition}>"
        
        children_repr = []
        for child in self.children:
            if isinstance(child, Q):
                children_repr.append(repr(child))
            elif isinstance(child, tuple):
                children_repr.append(f"{child[0]}={child[1]!r}")
            else:
                children_repr.append(repr(child))
        
        connector_name = self._connector.name
        prefix = "~" if self._negated else ""
        
        if len(children_repr) == 0:
            return f"<Q: {prefix}empty>"
        elif len(children_repr) == 1:
            return f"<Q: {prefix}{children_repr[0]}>"
        else:
            return f"<Q: {prefix}{connector_name}({', '.join(children_repr)})>"
    
    def copy(self) -> "Q":
        """Create a copy of this Q object."""
        obj = Q(_connector=self._connector, _negated=self._negated)
        obj.children = []
        obj._condition = self._condition
        
        for child in self.children:
            if isinstance(child, Q):
                obj.children.append(child.copy())
            else:
                obj.children.append(child)
        
        return obj
    
    def combine(self, other: "Q", connector: Connector) -> "Q":
        """
        Combine this Q object with another using the given connector.
        
        Args:
            other: Another Q object to combine with
            connector: How to combine (AND/OR)
        
        Returns:
            Combined Q object
        """
        if not isinstance(other, Q):
            raise TypeError(f"Cannot combine Q with {type(other).__name__}")
        
        if not self.children:
            return other.copy()
        
        if not other.children:
            return self.copy()
        
        combined = Q(_connector=connector)
        combined.add(self, connector)
        combined.add(other, connector)
        
        return combined
    
    def add(self, data: Any, connector: Connector) -> None:
        """
        Add data to this Q object.
        
        Args:
            data: Q object, dict, or tuple to add
            connector: How to connect (AND/OR)
        """
        super().add(data, connector)


class Value(Expression):
    """
    Expression wrapping a simple value.
    
    Used internally when combining expressions with values,
    but can also be used explicitly.
    
    Example:
        >>> Value(100)
        Value(100)
        
        >>> F('price') + Value(10)
        CombinedExpression(F('price'), '+', Value(10))
    """
    
    def __init__(
        self,
        value: Any,
        output_field: Any = None,
    ) -> None:
        """
        Initialize a Value expression.
        
        Args:
            value: The value to wrap
            output_field: Optional field type for the value
        """
        self.value = value
        self.output_field = output_field
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """Generate SQL for the value."""
        return "?", [self.value]
    
    def __repr__(self) -> str:
        return f"Value({self.value!r})"
    
    def __eq__(self, other: Any) -> bool:  # type: ignore
        if isinstance(other, Value):
            return self.value == other.value
        return self.value == other
    
    def __hash__(self) -> int:
        return hash(self.value)
    
    def copy(self) -> "Value":
        return Value(self.value, self.output_field)


class ExpressionWrapper(Expression, Combinable):
    """
    Wraps an expression with type information.
    
    Used to explicitly specify the output type of an expression.
    
    Example:
        >>> ExpressionWrapper(
        ...     F('price') * F('quantity'),
        ...     output_field=FloatField()
        ... )
    """
    
    def __init__(self, expression: Expression, output_field: Any) -> None:
        """
        Initialize an ExpressionWrapper.
        
        Args:
            expression: The expression to wrap
            output_field: The output field type
        """
        self.expression = expression
        self.output_field = output_field
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """Generate SQL for the wrapped expression."""
        return self.expression.as_sql()
    
    def __repr__(self) -> str:
        return f"ExpressionWrapper({self.expression!r}, output_field={self.output_field!r})"
    
    def copy(self) -> "ExpressionWrapper":
        return ExpressionWrapper(
            self.expression.copy(),
            self.output_field,
        )


class RawSQL(Expression):
    """
    Expression for raw SQL fragments.
    
    Allows embedding raw SQL in queries when needed.
    
    Example:
        >>> RawSQL("NOW()")
        RawSQL('NOW()', [])
        
        >>> RawSQL("EXTRACT(year FROM created_at) = %s", [2024])
        RawSQL('EXTRACT(year FROM created_at) = %s', [2024])
    """
    
    def __init__(self, sql: str, params: list[Any] | None = None) -> None:
        """
        Initialize a RawSQL expression.
        
        Args:
            sql: Raw SQL string
            params: Parameters for the SQL
        """
        self.sql = sql
        self.params = params or []
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """Return the raw SQL and params."""
        return self.sql, list(self.params)
    
    def __repr__(self) -> str:
        return f"RawSQL({self.sql!r}, {self.params!r})"
    
    def __eq__(self, other: Any) -> bool:  # type: ignore
        if isinstance(other, RawSQL):
            return self.sql == other.sql and self.params == other.params
        return False
    
    def __hash__(self) -> int:
        return hash((self.sql, tuple(self.params)))
    
    def copy(self) -> "RawSQL":
        return RawSQL(self.sql, list(self.params))


class When(Expression):
    """
    Condition for use in Case expressions.
    
    Represents a WHEN condition with a THEN result.
    
    Example:
        >>> When(Q(status='active'), then=Value('Active'))
        When(Q(status='active'), then=Value('Active'))
    """
    
    def __init__(
        self,
        condition: Q | ExpressionCondition | None = None,
        then: Expression | None = None,
        *,
        **lookups: Any,
    ) -> None:
        """
        Initialize a When clause.
        
        Args:
            condition: Q object or ExpressionCondition for the WHEN
            then: Expression for the THEN result
            **lookups: Field lookups as an alternative to Q object
        """
        if condition is None and not lookups:
            raise ValueError("When requires either a condition or lookups")
        
        if condition is not None and lookups:
            raise ValueError("When cannot have both condition and lookups")
        
        if lookups:
            self.condition = Q(**lookups)
        else:
            self.condition = condition if isinstance(condition, Q) else Q(_condition=condition)
        
        if then is None:
            raise ValueError("When requires a 'then' expression")
        self.result = then if isinstance(then, Expression) else Value(then)
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """Generate SQL for the WHEN clause."""
        condition_sql, condition_params = self.condition.as_sql()
        result_sql, result_params = self.result.as_sql()
        
        sql = f"WHEN {condition_sql} THEN {result_sql}"
        return sql, condition_params + result_params
    
    def __repr__(self) -> str:
        return f"When({self.condition!r}, then={self.result!r})"
    
    def copy(self) -> "When":
        return When(
            condition=self.condition.copy(),
            then=self.result.copy(),
        )


class Case(Expression):
    """
    Case expression for conditional SQL.
    
    Similar to SQL CASE WHEN ... THEN ... ELSE ... END.
    
    Example:
        >>> Case(
        ...     When(Q(status='active'), then=Value('Active')),
        ...     When(Q(status='inactive'), then=Value('Inactive')),
        ...     default=Value('Unknown'),
        ... )
    """
    
    def __init__(
        self,
        *cases: When,
        default: Expression | Any = None,
    ) -> None:
        """
        Initialize a Case expression.
        
        Args:
            *cases: When clauses
            default: Default value if no conditions match
        """
        if not cases:
            raise ValueError("Case requires at least one When clause")
        
        self.cases = list(cases)
        if default is not None and not isinstance(default, Expression):
            default = Value(default)
        self.default = default
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """Generate SQL for the CASE expression."""
        parts: list[str] = []
        params: list[Any] = []
        
        for case in self.cases:
            case_sql, case_params = case.as_sql()
            parts.append(case_sql)
            params.extend(case_params)
        
        if self.default:
            default_sql, default_params = self.default.as_sql()
            parts.append(f"ELSE {default_sql}")
            params.extend(default_params)
        
        sql = "CASE " + " ".join(parts) + " END"
        return sql, params
    
    def __repr__(self) -> str:
        parts = [repr(case) for case in self.cases]
        if self.default:
            parts.append(f"default={self.default!r}")
        return f"Case({', '.join(parts)})"
    
    def copy(self) -> "Case":
        return Case(
            *[case.copy() for case in self.cases],
            default=self.default.copy() if self.default else None,
        )


class Func(Expression):
    """
    Base class for SQL function expressions.
    
    Example:
        >>> Func('COUNT', [F('id')])
        Func('COUNT', [F('id')])
    """
    
    def __init__(
        self,
        function: str,
        expressions: list[Expression] | None = None,
        output_field: Any = None,
        **extra: Any,
    ) -> None:
        """
        Initialize a Func expression.
        
        Args:
            function: SQL function name
            expressions: Arguments to the function
            output_field: Output field type
            **extra: Extra parameters
        """
        self.function = function
        self.expressions = expressions or []
        self.output_field = output_field
        self.extra = extra
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """Generate SQL for the function call."""
        parts: list[str] = []
        params: list[Any] = []
        
        for expr in self.expressions:
            expr_sql, expr_params = expr.as_sql()
            parts.append(expr_sql)
            params.extend(expr_params)
        
        sql = f"{self.function}({', '.join(parts)})"
        return sql, params
    
    def __repr__(self) -> str:
        return f"Func({self.function!r}, {self.expressions!r})"
    
    def copy(self) -> "Func":
        return Func(
            self.function,
            [e.copy() for e in self.expressions],
            self.output_field,
            **self.extra,
        )


class Subquery(Expression):
    """
    Subquery expression for nested queries.
    
    Example:
        >>> Subquery(
        ...     Order.filter(user_id=F('id'))
        ...         .values('total')
        ...         .order_by('-created_at')[:1]
        ... )
    """
    
    def __init__(
        self,
        queryset: Any,
        output_field: Any = None,
    ) -> None:
        """
        Initialize a Subquery expression.
        
        Args:
            queryset: The queryset to use as subquery
            output_field: Output field type
        """
        self.queryset = queryset
        self.output_field = output_field
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """Generate SQL for the subquery."""
        if hasattr(self.queryset, 'query'):
            query = self.queryset.query
            return query.as_sql()
        return "(SELECT 1)", []
    
    def __repr__(self) -> str:
        return f"Subquery({self.queryset!r})"
    
    def copy(self) -> "Subquery":
        return Subquery(self.queryset, self.output_field)


class Exists(Expression):
    """
    EXISTS subquery expression.
    
    Returns True if the subquery returns any rows.
    
    Example:
        >>> Exists(Order.filter(user_id=F('id')))
        Exists(<QuerySet>)
    """
    
    def __init__(
        self,
        queryset: Any,
        negated: bool = False,
    ) -> None:
        """
        Initialize an Exists expression.
        
        Args:
            queryset: The queryset to check for existence
            negated: If True, returns NOT EXISTS
        """
        self.queryset = queryset
        self.negated = negated
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """Generate SQL for the EXISTS clause."""
        if hasattr(self.queryset, 'query'):
            query = self.queryset.query
            subquery_sql, params = query.as_sql()
        else:
            subquery_sql, params = "(SELECT 1)", []
        
        if self.negated:
            return f"NOT EXISTS ({subquery_sql})", params
        return f"EXISTS ({subquery_sql})", params
    
    def __repr__(self) -> str:
        prefix = "~" if self.negated else ""
        return f"{prefix}Exists({self.queryset!r})"
    
    def __invert__(self) -> "Exists":
        """Negate the EXISTS (returns NOT EXISTS)."""
        return Exists(self.queryset, negated=not self.negated)
    
    def copy(self) -> "Exists":
        return Exists(self.queryset, self.negated)


# Aggregate expressions
class Aggregate(Func):
    """
    Base class for aggregate functions.
    
    Example:
        >>> Aggregate('SUM', [F('price')], filter=Q(active=True))
    """
    
    contains_aggregate = True
    
    def __init__(
        self,
        expression: Expression | str,
        function: str,
        filter: Q | None = None,
        distinct: bool = False,
        output_field: Any = None,
        **extra: Any,
    ) -> None:
        """
        Initialize an Aggregate expression.
        
        Args:
            expression: The expression to aggregate
            function: SQL function name (SUM, COUNT, AVG, etc.)
            filter: Optional Q object to filter aggregated rows
            distinct: If True, use DISTINCT in aggregate
            output_field: Output field type
        """
        if isinstance(expression, str):
            expression = F(expression)
        
        super().__init__(function, [expression], output_field, **extra)
        self.filter = filter
        self.distinct = distinct
    
    def as_sql(self) -> tuple[str, list[Any]]:
        """Generate SQL for the aggregate function."""
        expr_sql, params = self.expressions[0].as_sql()
        
        if self.distinct:
            sql = f"{self.function}(DISTINCT {expr_sql})"
        else:
            sql = f"{self.function}({expr_sql})"
        
        if self.filter:
            filter_sql, filter_params = self.filter.as_sql()
            sql = f"{sql} FILTER (WHERE {filter_sql})"
            params.extend(filter_params)
        
        return sql, params
    
    def __repr__(self) -> str:
        return f"{self.function}({self.expressions[0]!r})"


class Count(Aggregate):
    """COUNT aggregate function."""
    
    def __init__(
        self,
        expression: Expression | str = "*",
        distinct: bool = False,
        filter: Q | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(expression, "COUNT", filter=filter, distinct=distinct, **extra)


class Sum(Aggregate):
    """SUM aggregate function."""
    
    def __init__(
        self,
        expression: Expression | str,
        distinct: bool = False,
        filter: Q | None = None,
        output_field: Any = None,
        **extra: Any,
    ) -> None:
        super().__init__(expression, "SUM", filter=filter, distinct=distinct, output_field=output_field, **extra)


class Avg(Aggregate):
    """AVG aggregate function."""
    
    def __init__(
        self,
        expression: Expression | str,
        distinct: bool = False,
        filter: Q | None = None,
        output_field: Any = None,
        **extra: Any,
    ) -> None:
        super().__init__(expression, "AVG", filter=filter, distinct=distinct, output_field=output_field, **extra)


class Max(Aggregate):
    """MAX aggregate function."""
    
    def __init__(
        self,
        expression: Expression | str,
        filter: Q | None = None,
        output_field: Any = None,
        **extra: Any,
    ) -> None:
        super().__init__(expression, "MAX", filter=filter, output_field=output_field, **extra)


class Min(Aggregate):
    """MIN aggregate function."""
    
    def __init__(
        self,
        expression: Expression | str,
        filter: Q | None = None,
        output_field: Any = None,
        **extra: Any,
    ) -> None:
        super().__init__(expression, "MIN", filter=filter, output_field=output_field, **extra)


# Convenience exports
__all__ = [
    # Core expressions
    "Expression",
    "Combinable",
    "CombinedExpression",
    "ExpressionCondition",
    
    # Q and F
    "Q",
    "F",
    
    # Value expressions
    "Value",
    "ExpressionWrapper",
    "RawSQL",
    
    # Conditional expressions
    "When",
    "Case",
    
    # Subquery expressions
    "Subquery",
    "Exists",
    
    # Function expressions
    "Func",
    
    # Aggregate expressions
    "Aggregate",
    "Count",
    "Sum",
    "Avg",
    "Max",
    "Min",
]
