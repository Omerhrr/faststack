"""
Database functions for ORM queries.
"""

from faststack.faststack.orm.query.functions import (
    # Text functions
    Concat, Lower, Upper, Length, Trim, LTrim, RTrim,
    Substr, Replace, Reverse, StrIndex, Left, Right, Pad,
    # Math functions
    Abs, Ceil, Floor, Round, Power, Sqrt, Sign,
    Mod, Exp, Ln, Log,
    # Date functions
    Extract, Now, Trunc, TruncDate, TruncTime, TruncYear, TruncMonth, TruncDay,
    # Aggregate functions
    Count, Sum, Avg, Min, Max, StdDev, Variance,
    # Other functions
    Coalesce, Cast, Greatest, Least, NullIf, Random,
)

__all__ = [
    # Text functions
    'Concat', 'Lower', 'Upper', 'Length', 'Trim', 'LTrim', 'RTrim',
    'Substr', 'Replace', 'Reverse', 'StrIndex', 'Left', 'Right', 'Pad',
    # Math functions
    'Abs', 'Ceil', 'Floor', 'Round', 'Power', 'Sqrt', 'Sign',
    'Mod', 'Exp', 'Ln', 'Log',
    # Date functions
    'Extract', 'Now', 'Trunc', 'TruncDate', 'TruncTime', 'TruncYear', 'TruncMonth', 'TruncDay',
    # Aggregate functions
    'Count', 'Sum', 'Avg', 'Min', 'Max', 'StdDev', 'Variance',
    # Other functions
    'Coalesce', 'Cast', 'Greatest', 'Least', 'NullIf', 'Random',
]
