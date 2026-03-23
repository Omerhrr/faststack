"""
Database Functions for FastStack ORM.

Provides database-side functions that can be used in queries,
annotations, and updates.

Example:
    from faststack.orm.query import Lower, Concat, Count

    # Use in annotation
    await User.annotate(name_lower=Lower('name'))

    # Use in filter
    await User.filter(Lower('name') == 'john')

    # Use in update
    await User.update(name=Concat('first_name', Value(' '), 'last_name'))
"""

from typing import Any, List, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement
    from .f import F
    from .expressions import Value


class SQLFunction(ABC):
    """Base class for SQL functions."""

    # Function name in SQL
    name: str = ''

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(...)"

    @abstractmethod
    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        """Convert to SQLAlchemy function call."""
        pass

    def __eq__(self, other: Any) -> 'Comparison':
        """Create equality comparison."""
        return Comparison(self, '==', other)

    def __ne__(self, other: Any) -> 'Comparison':
        """Create inequality comparison."""
        return Comparison(self, '!=', other)

    def __gt__(self, other: Any) -> 'Comparison':
        """Create greater than comparison."""
        return Comparison(self, '>', other)

    def __ge__(self, other: Any) -> 'Comparison':
        """Create greater or equal comparison."""
        return Comparison(self, '>=', other)

    def __lt__(self, other: Any) -> 'Comparison':
        """Create less than comparison."""
        return Comparison(self, '<', other)

    def __le__(self, other: Any) -> 'Comparison':
        """Create less or equal comparison."""
        return Comparison(self, '<=', other)


@dataclass
class Comparison:
    """Comparison expression for function results."""

    function: SQLFunction
    operator: str
    value: Any

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        """Convert to SQLAlchemy comparison."""
        from sqlalchemy import literal

        func_expr = self.function.to_sqlalchemy(model)

        if isinstance(self.value, (F, SQLFunction)):
            value_expr = self.value.to_sqlalchemy(model)
        else:
            value_expr = literal(self.value)

        if self.operator == '==':
            return func_expr == value_expr
        elif self.operator == '!=':
            return func_expr != value_expr
        elif self.operator == '>':
            return func_expr > value_expr
        elif self.operator == '>=':
            return func_expr >= value_expr
        elif self.operator == '<':
            return func_expr < value_expr
        elif self.operator == '<=':
            return func_expr <= value_expr

        raise ValueError(f"Unknown operator: {self.operator}")


def resolve_arg(arg: Any, model: type) -> 'ColumnElement':
    """Resolve argument to SQLAlchemy expression."""
    from sqlalchemy import literal
    from .f import F
    from .expressions import Value

    if isinstance(arg, F):
        return arg.to_sqlalchemy(model)
    elif isinstance(arg, SQLFunction):
        return arg.to_sqlalchemy(model)
    elif isinstance(arg, Value):
        return arg.to_sqlalchemy(model)
    else:
        return literal(arg)


# =============================================================================
# Text Functions
# =============================================================================

class Concat(SQLFunction):
    """
    Concatenate strings.

    SQL: CONCAT(arg1, arg2, ...)

    Example:
        Concat('first_name', ' ', 'last_name')
        Concat(F('prefix'), F('name'))
    """

    name = 'CONCAT'

    def __init__(self, *args: Any):
        self.args = list(args)

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        resolved = [resolve_arg(arg, model) for arg in self.args]
        return func.concat(*resolved)


class Lower(SQLFunction):
    """
    Convert string to lowercase.

    SQL: LOWER(field)

    Example:
        Lower('name')
        Lower(F('email'))
    """

    name = 'LOWER'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.lower(resolve_arg(self.expression, model))


class Upper(SQLFunction):
    """
    Convert string to uppercase.

    SQL: UPPER(field)
    """

    name = 'UPPER'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.upper(resolve_arg(self.expression, model))


class Length(SQLFunction):
    """
    Get string length.

    SQL: LENGTH(field)
    """

    name = 'LENGTH'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.length(resolve_arg(self.expression, model))


class Trim(SQLFunction):
    """
    Remove leading and trailing whitespace.

    SQL: TRIM(field)
    """

    name = 'TRIM'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.trim(resolve_arg(self.expression, model))


class LTrim(SQLFunction):
    """
    Remove leading whitespace.

    SQL: LTRIM(field)
    """

    name = 'LTRIM'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.ltrim(resolve_arg(self.expression, model))


class RTrim(SQLFunction):
    """
    Remove trailing whitespace.

    SQL: RTRIM(field)
    """

    name = 'RTRIM'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.rtrim(resolve_arg(self.expression, model))


class Substr(SQLFunction):
    """
    Extract substring.

    SQL: SUBSTRING(field, start, length)

    Example:
        Substr('name', 1, 5)  # First 5 characters
    """

    name = 'SUBSTR'

    def __init__(self, expression: Any, start: int, length: Optional[int] = None):
        self.expression = expression
        self.start = start
        self.length = length

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        arg = resolve_arg(self.expression, model)
        if self.length:
            return func.substr(arg, self.start, self.length)
        return func.substr(arg, self.start)


class Replace(SQLFunction):
    """
    Replace occurrences of a string.

    SQL: REPLACE(field, from_str, to_str)

    Example:
        Replace('content', 'old', 'new')
    """

    name = 'REPLACE'

    def __init__(self, expression: Any, from_str: str, to_str: str):
        self.expression = expression
        self.from_str = from_str
        self.to_str = to_str

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.replace(
            resolve_arg(self.expression, model),
            self.from_str,
            self.to_str
        )


class Reverse(SQLFunction):
    """
    Reverse a string.

    SQL: REVERSE(field)
    """

    name = 'REVERSE'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.reverse(resolve_arg(self.expression, model))


class StrIndex(SQLFunction):
    """
    Find position of substring.

    SQL: STRPOS(field, substring) or INSTR(field, substring)

    Returns 0 if not found.
    """

    name = 'STRPOS'

    def __init__(self, expression: Any, substring: str):
        self.expression = expression
        self.substring = substring

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.strpos(resolve_arg(self.expression, model), self.substring)


class Left(SQLFunction):
    """
    Get leftmost N characters.

    SQL: LEFT(field, length)
    """

    name = 'LEFT'

    def __init__(self, expression: Any, length: int):
        self.expression = expression
        self.length = length

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.left(resolve_arg(self.expression, model), self.length)


class Right(SQLFunction):
    """
    Get rightmost N characters.

    SQL: RIGHT(field, length)
    """

    name = 'RIGHT'

    def __init__(self, expression: Any, length: int):
        self.expression = expression
        self.length = length

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.right(resolve_arg(self.expression, model), self.length)


class Pad(SQLFunction):
    """
    Pad string to specified length.

    SQL: LPAD or RPAD

    Example:
        Pad('code', 10, '0', side='left')  # '000000code'
    """

    name = 'PAD'

    def __init__(self, expression: Any, length: int, pad_char: str = ' ', side: str = 'right'):
        self.expression = expression
        self.length = length
        self.pad_char = pad_char
        self.side = side

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        arg = resolve_arg(self.expression, model)
        if self.side == 'left':
            return func.lpad(arg, self.length, self.pad_char)
        return func.rpad(arg, self.length, self.pad_char)


# =============================================================================
# Math Functions
# =============================================================================

class Abs(SQLFunction):
    """
    Absolute value.

    SQL: ABS(field)
    """

    name = 'ABS'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.abs(resolve_arg(self.expression, model))


class Ceil(SQLFunction):
    """
    Ceiling (smallest integer >= value).

    SQL: CEIL(field) or CEILING(field)
    """

    name = 'CEIL'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.ceil(resolve_arg(self.expression, model))


class Floor(SQLFunction):
    """
    Floor (largest integer <= value).

    SQL: FLOOR(field)
    """

    name = 'FLOOR'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.floor(resolve_arg(self.expression, model))


class Round(SQLFunction):
    """
    Round to specified decimal places.

    SQL: ROUND(field, precision)

    Example:
        Round('price', 2)
    """

    name = 'ROUND'

    def __init__(self, expression: Any, precision: int = 0):
        self.expression = expression
        self.precision = precision

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.round(resolve_arg(self.expression, model), self.precision)


class Power(SQLFunction):
    """
    Raise to power.

    SQL: POWER(base, exponent) or POW(base, exponent)

    Example:
        Power('value', 2)  # value^2
    """

    name = 'POWER'

    def __init__(self, expression: Any, exponent: Union[int, float]):
        self.expression = expression
        self.exponent = exponent

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.power(resolve_arg(self.expression, model), self.exponent)


class Sqrt(SQLFunction):
    """
    Square root.

    SQL: SQRT(field)
    """

    name = 'SQRT'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.sqrt(resolve_arg(self.expression, model))


class Sign(SQLFunction):
    """
    Sign of number (-1, 0, or 1).

    SQL: SIGN(field)
    """

    name = 'SIGN'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.sign(resolve_arg(self.expression, model))


class Mod(SQLFunction):
    """
    Modulo operation.

    SQL: MOD(field, divisor)

    Example:
        Mod('value', 10)
    """

    name = 'MOD'

    def __init__(self, expression: Any, divisor: Union[int, float]):
        self.expression = expression
        self.divisor = divisor

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.mod(resolve_arg(self.expression, model), self.divisor)


class Exp(SQLFunction):
    """
    Exponential (e^x).

    SQL: EXP(field)
    """

    name = 'EXP'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.exp(resolve_arg(self.expression, model))


class Ln(SQLFunction):
    """
    Natural logarithm.

    SQL: LN(field)
    """

    name = 'LN'

    def __init__(self, expression: Any):
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.ln(resolve_arg(self.expression, model))


class Log(SQLFunction):
    """
    Logarithm.

    SQL: LOG(base, field) or LOG(field)

    Example:
        Log('value', 10)  # log base 10
    """

    name = 'LOG'

    def __init__(self, expression: Any, base: Optional[float] = None):
        self.expression = expression
        self.base = base

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        arg = resolve_arg(self.expression, model)
        if self.base:
            return func.log(self.base, arg)
        return func.log(arg)


# =============================================================================
# Date/Time Functions
# =============================================================================

class Extract(SQLFunction):
    """
    Extract date/time component.

    SQL: EXTRACT(component FROM field)

    Example:
        Extract('year', 'created_at')
        Extract('month', 'date_joined')
    """

    name = 'EXTRACT'

    VALID_COMPONENTS = {
        'year', 'month', 'day', 'hour', 'minute', 'second',
        'dow', 'doy', 'week', 'quarter', 'epoch'
    }

    def __init__(self, component: str, expression: Any):
        if component.lower() not in self.VALID_COMPONENTS:
            raise ValueError(f"Invalid component: {component}. Valid: {self.VALID_COMPONENTS}")
        self.component = component.lower()
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import extract
        return extract(self.component, resolve_arg(self.expression, model))


class Now(SQLFunction):
    """
    Current timestamp.

    SQL: NOW() or CURRENT_TIMESTAMP
    """

    name = 'NOW'

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.now()


class Trunc(SQLFunction):
    """
    Truncate date/time to specified precision.

    SQL: DATE_TRUNC(precision, field)

    Example:
        Trunc('day', 'created_at')
        Trunc('month', 'date_joined')
    """

    name = 'TRUNC'

    VALID_PRECISIONS = {
        'year', 'quarter', 'month', 'week', 'day',
        'hour', 'minute', 'second'
    }

    def __init__(self, precision: str, expression: Any):
        if precision.lower() not in self.VALID_PRECISIONS:
            raise ValueError(f"Invalid precision: {precision}. Valid: {self.VALID_PRECISIONS}")
        self.precision = precision.lower()
        self.expression = expression

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.date_trunc(self.precision, resolve_arg(self.expression, model))


class TruncDate(Trunc):
    """Truncate to date (remove time component)."""

    def __init__(self, expression: Any):
        super().__init__('day', expression)


class TruncTime(Trunc):
    """Truncate to time (remove date component)."""

    def __init__(self, expression: Any):
        # Note: This may need database-specific handling
        super().__init__('second', expression)


class TruncYear(Trunc):
    """Truncate to year."""

    def __init__(self, expression: Any):
        super().__init__('year', expression)


class TruncMonth(Trunc):
    """Truncate to month."""

    def __init__(self, expression: Any):
        super().__init__('month', expression)


class TruncDay(Trunc):
    """Truncate to day."""

    def __init__(self, expression: Any):
        super().__init__('day', expression)


# =============================================================================
# Aggregate Functions
# =============================================================================

class Aggregate(SQLFunction):
    """Base class for aggregate functions."""

    def __init__(
        self,
        expression: Any,
        distinct: bool = False,
        filter_: Optional[Any] = None
    ):
        self.expression = expression
        self.distinct = distinct
        self.filter = filter_


class Count(Aggregate):
    """
    Count aggregate.

    SQL: COUNT(field) or COUNT(*)

    Example:
        Count('id')
        Count('id', distinct=True)
        Count('*')
    """

    name = 'COUNT'

    def __init__(
        self,
        expression: Any = '*',
        distinct: bool = False,
        filter_: Optional[Any] = None
    ):
        super().__init__(expression, distinct, filter_)

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func, literal_column

        if self.expression == '*':
            arg = literal_column('*')
        else:
            arg = resolve_arg(self.expression, model)

        result = func.count(arg)

        if self.distinct:
            result = func.count(arg.distinct())

        return result


class Sum(Aggregate):
    """
    Sum aggregate.

    SQL: SUM(field)

    Example:
        Sum('price')
        Sum(F('quantity') * F('price'))
    """

    name = 'SUM'

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        arg = resolve_arg(self.expression, model)
        result = func.sum(arg)
        if self.distinct:
            result = func.sum(arg.distinct())
        return result


class Avg(Aggregate):
    """
    Average aggregate.

    SQL: AVG(field)
    """

    name = 'AVG'

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        arg = resolve_arg(self.expression, model)
        result = func.avg(arg)
        if self.distinct:
            result = func.avg(arg.distinct())
        return result


class Min(Aggregate):
    """
    Minimum aggregate.

    SQL: MIN(field)
    """

    name = 'MIN'

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.min(resolve_arg(self.expression, model))


class Max(Aggregate):
    """
    Maximum aggregate.

    SQL: MAX(field)
    """

    name = 'MAX'

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.max(resolve_arg(self.expression, model))


class StdDev(Aggregate):
    """
    Standard deviation aggregate.

    SQL: STDDEV(field) or STDDEV_SAMP(field)
    """

    name = 'STDDEV'

    def __init__(self, expression: Any, sample: bool = True):
        super().__init__(expression)
        self.sample = sample

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        if self.sample:
            return func.stddev_samp(resolve_arg(self.expression, model))
        return func.stddev_pop(resolve_arg(self.expression, model))


class Variance(Aggregate):
    """
    Variance aggregate.

    SQL: VARIANCE(field) or VAR_SAMP(field)
    """

    name = 'VARIANCE'

    def __init__(self, expression: Any, sample: bool = True):
        super().__init__(expression)
        self.sample = sample

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        if self.sample:
            return func.var_samp(resolve_arg(self.expression, model))
        return func.var_pop(resolve_arg(self.expression, model))


# =============================================================================
# Other Functions
# =============================================================================

class Coalesce(SQLFunction):
    """
    Return first non-null argument.

    SQL: COALESCE(arg1, arg2, ...)

    Example:
        Coalesce('nickname', 'username', Value('Anonymous'))
    """

    name = 'COALESCE'

    def __init__(self, *args: Any):
        if not args:
            raise ValueError("Coalesce requires at least one argument")
        self.args = list(args)

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        resolved = [resolve_arg(arg, model) for arg in self.args]
        return func.coalesce(*resolved)


class Cast(SQLFunction):
    """
    Cast expression to specified type.

    SQL: CAST(field AS type)

    Example:
        Cast('price', 'FLOAT')
        Cast('id', 'VARCHAR')
    """

    name = 'CAST'

    VALID_TYPES = {
        'INTEGER', 'BIGINT', 'SMALLINT',
        'FLOAT', 'DOUBLE', 'DECIMAL',
        'VARCHAR', 'CHAR', 'TEXT',
        'BOOLEAN', 'DATE', 'TIME', 'TIMESTAMP',
        'JSON', 'JSONB'
    }

    def __init__(self, expression: Any, output_type: str):
        if output_type.upper() not in self.VALID_TYPES:
            raise ValueError(f"Invalid type: {output_type}. Valid: {self.VALID_TYPES}")
        self.expression = expression
        self.output_type = output_type.upper()

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import cast, String, Integer, Float, Boolean, Date, DateTime
        from sqlalchemy.dialects.postgresql import JSONB

        type_map = {
            'INTEGER': Integer,
            'BIGINT': Integer,
            'FLOAT': Float,
            'DOUBLE': Float,
            'VARCHAR': String,
            'CHAR': String,
            'TEXT': String,
            'BOOLEAN': Boolean,
            'DATE': Date,
            'TIMESTAMP': DateTime,
        }

        sa_type = type_map.get(self.output_type, String)
        return cast(resolve_arg(self.expression, model), sa_type)


class Greatest(SQLFunction):
    """
    Return the greatest (maximum) value.

    SQL: GREATEST(arg1, arg2, ...)

    Example:
        Greatest('a', 'b', 'c')
    """

    name = 'GREATEST'

    def __init__(self, *args: Any):
        if not args:
            raise ValueError("Greatest requires at least one argument")
        self.args = list(args)

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        resolved = [resolve_arg(arg, model) for arg in self.args]
        return func.greatest(*resolved)


class Least(SQLFunction):
    """
    Return the least (minimum) value.

    SQL: LEAST(arg1, arg2, ...)

    Example:
        Least('a', 'b', 'c')
    """

    name = 'LEAST'

    def __init__(self, *args: Any):
        if not args:
            raise ValueError("Least requires at least one argument")
        self.args = list(args)

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        resolved = [resolve_arg(arg, model) for arg in self.args]
        return func.least(*resolved)


class NullIf(SQLFunction):
    """
    Return NULL if two values are equal.

    SQL: NULLIF(arg1, arg2)

    Example:
        NullIf('value', 0)  # Returns NULL if value is 0
    """

    name = 'NULLIF'

    def __init__(self, expression1: Any, expression2: Any):
        self.expression1 = expression1
        self.expression2 = expression2

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.nullif(
            resolve_arg(self.expression1, model),
            resolve_arg(self.expression2, model)
        )


class Random(SQLFunction):
    """
    Generate random number.

    SQL: RANDOM() or RAND()

    Returns: Float between 0 and 1
    """

    name = 'RANDOM'

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        from sqlalchemy import func
        return func.random()
