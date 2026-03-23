"""
Query optimization functions.
"""

from faststack.faststack.orm.query.optimization import (
    select_related,
    prefetch_related,
    QueryOptimizer,
    Prefetch,
    OptimizableQuerySet,
    RelatedField,
)

__all__ = [
    'select_related',
    'prefetch_related',
    'QueryOptimizer',
    'Prefetch',
    'OptimizableQuerySet',
    'RelatedField',
]
