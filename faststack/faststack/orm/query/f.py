"""
F Expressions for atomic field updates and comparisons.

F() references allow using model field values in queries without
pulling them into Python memory. This enables:

1. Atomic updates: F('views') + 1 instead of read-modify-write
2. Field comparisons: Filter where field_a > field_b
3. Annotations with field values

Example:
    from faststack.orm.query import F

    # Atomic update
    await Post.filter(id=1).update(views=F('views') + 1)

    # Field comparison in filter
    await User.filter(age__gt=F('required_age'))

    # Annotation
    await Product.annotate(discount_pct=F('discount') * 100 / F('price'))
"""

from typing import Any, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
import copy

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement


class ArithmeticOp(Enum):
    """Arithmetic operations for F expressions."""
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    MOD = "%"
    POW = "^"


@dataclass
class F:
    """
    F expression for referencing model field values in queries.

    F expressions allow you to reference model field values and perform
    database-level operations without pulling data into Python memory.

    Example:
        # Atomic increment
        await Post.filter(id=1).update(views=F('views') + 1)

        # Multiple operations
        await Product.filter(id=1).update(
            price=F('price') * F('markup') + F('base_cost')
        )

        # Field comparisons
        await User.filter(age__gte=F('retirement_age') - 10)

        # Use in annotations
        await Order.annotate(
            total=F('quantity') * F('unit_price')
        )
    """

    # Field name being referenced
    name: str

    # Optional arithmetic expression
    _expression: Optional['FExpression'] = None

    def __init__(self, name: str):
        """
        Initialize F expression.

        Args:
            name: Field name to reference
        """
        self.name = name
        self._expression = None

    def __repr__(self) -> str:
        if self._expression:
            return f"F({self._expression})"
        return f"F('{self.name}')"

    def __add__(self, other: Union['F', int, float]) -> 'F':
        """Add: F('field') + 1 or F('field1') + F('field2')"""
        return self._create_expression(ArithmeticOp.ADD, other)

    def __radd__(self, other: Union['F', int, float]) -> 'F':
        """Right add: 1 + F('field')"""
        return self._create_expression(ArithmeticOp.ADD, other, reverse=True)

    def __sub__(self, other: Union['F', int, float]) -> 'F':
        """Subtract: F('field') - 1"""
        return self._create_expression(ArithmeticOp.SUB, other)

    def __rsub__(self, other: Union['F', int, float]) -> 'F':
        """Right subtract: 1 - F('field')"""
        return self._create_expression(ArithmeticOp.SUB, other, reverse=True)

    def __mul__(self, other: Union['F', int, float]) -> 'F':
        """Multiply: F('field') * 2"""
        return self._create_expression(ArithmeticOp.MUL, other)

    def __rmul__(self, other: Union['F', int, float]) -> 'F':
        """Right multiply: 2 * F('field')"""
        return self._create_expression(ArithmeticOp.MUL, other, reverse=True)

    def __truediv__(self, other: Union['F', int, float]) -> 'F':
        """Divide: F('field') / 2"""
        return self._create_expression(ArithmeticOp.DIV, other)

    def __rtruediv__(self, other: Union['F', int, float]) -> 'F':
        """Right divide: 100 / F('field')"""
        return self._create_expression(ArithmeticOp.DIV, other, reverse=True)

    def __mod__(self, other: Union['F', int, float]) -> 'F':
        """Modulo: F('field') % 10"""
        return self._create_expression(ArithmeticOp.MOD, other)

    def __rmod__(self, other: Union['F', int, float]) -> 'F':
        """Right modulo: 100 % F('field')"""
        return self._create_expression(ArithmeticOp.MOD, other, reverse=True)

    def __pow__(self, other: Union['F', int, float]) -> 'F':
        """Power: F('field') ** 2"""
        return self._create_expression(ArithmeticOp.POW, other)

    def __rpow__(self, other: Union['F', int, float]) -> 'F':
        """Right power: 2 ** F('field')"""
        return self._create_expression(ArithmeticOp.POW, other, reverse=True)

    def __neg__(self) -> 'F':
        """Negate: -F('field')"""
        return self * -1

    def __abs__(self) -> 'F':
        """Absolute: abs(F('field'))"""
        from .functions import Abs
        return Abs(self)

    def _create_expression(
        self,
        op: ArithmeticOp,
        other: Union['F', int, float],
        reverse: bool = False
    ) -> 'F':
        """Create a new F expression with arithmetic operation."""
        result = F(self.name)
        left = FExpression(self.name) if self._expression is None else self._expression

        if isinstance(other, F):
            right = FExpression(other.name) if other._expression is None else other._expression
        else:
            right = FExpression(value=other)

        if reverse:
            result._expression = FExpression(operator=op, left=right, right=left)
        else:
            result._expression = FExpression(operator=op, left=left, right=right)

        return result

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        """
        Convert F expression to SQLAlchemy expression.

        Args:
            model: SQLAlchemy model class

        Returns:
            SQLAlchemy ColumnElement expression
        """
        if not hasattr(model, self.name):
            raise AttributeError(f"Model {model.__name__} has no field '{self.name}'")

        column = getattr(model, self.name)

        if self._expression:
            return self._expression.to_sqlalchemy(model)

        return column

    def resolve(self, model: type) -> 'ColumnElement':
        """Alias for to_sqlalchemy."""
        return self.to_sqlalchemy(model)


@dataclass
class FExpression:
    """
    Internal expression tree for F expressions.

    Stores the structure of arithmetic expressions for later
    conversion to SQLAlchemy.
    """

    # Field name (for leaf nodes)
    field: Optional[str] = None

    # Literal value (for leaf nodes)
    value: Optional[Union[int, float]] = None

    # Operator (for internal nodes)
    operator: Optional[ArithmeticOp] = None

    # Left operand (for binary operations)
    left: Optional['FExpression'] = None

    # Right operand (for binary operations)
    right: Optional['FExpression'] = None

    def __repr__(self) -> str:
        if self.field:
            return f"F('{self.field}')"
        if self.value is not None:
            return str(self.value)
        if self.operator and self.left and self.right:
            return f"({self.left} {self.operator.value} {self.right})"
        return "FExpression()"

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        """Convert expression to SQLAlchemy."""
        from sqlalchemy import literal

        if self.field:
            if not hasattr(model, self.field):
                raise AttributeError(f"Model {model.__name__} has no field '{self.field}'")
            return getattr(model, self.field)

        if self.value is not None:
            return literal(self.value)

        if self.operator and self.left and self.right:
            left_expr = self.left.to_sqlalchemy(model)
            right_expr = self.right.to_sqlalchemy(model)

            if self.operator == ArithmeticOp.ADD:
                return left_expr + right_expr
            elif self.operator == ArithmeticOp.SUB:
                return left_expr - right_expr
            elif self.operator == ArithmeticOp.MUL:
                return left_expr * right_expr
            elif self.operator == ArithmeticOp.DIV:
                return left_expr / right_expr
            elif self.operator == ArithmeticOp.MOD:
                return left_expr % right_expr
            elif self.operator == ArithmeticOp.POW:
                return left_expr.pow(right_expr)

        raise ValueError("Invalid F expression")


class ExpressionWrapper:
    """
    Wrapper for complex expressions combining F, annotations, and aggregates.

    Example:
        ExpressionWrapper(
            F('price') * F('quantity'),
            output_field=FloatField()
        )
    """

    def __init__(self, expression: Any, output_field: Any = None):
        self.expression = expression
        self.output_field = output_field

    def to_sqlalchemy(self, model: type) -> 'ColumnElement':
        if isinstance(self.expression, F):
            return self.expression.to_sqlalchemy(model)
        return self.expression
