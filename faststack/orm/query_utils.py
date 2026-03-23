"""
FastStack ORM Query Utilities

Provides utilities for parsing lookups and building query trees.
Django-compatible but designed for async-first operations.

Features:
- Lookup parsing (field__lookup=value)
- Node class for query tree structure
- Query tree traversal and manipulation
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Iterator
from collections.abc import Iterable


class Connector(Enum):
    """Logical connectors for combining query conditions."""
    AND = "AND"
    OR = "OR"


# Default lookup names supported by the ORM
DEFAULT_LOOKUPS = frozenset({
    "exact", "iexact", "contains", "icontains",
    "startswith", "istartswith", "endswith", "iendswith",
    "gt", "gte", "lt", "lte",
    "in", "isnull", "regex", "iregex",
    "range", "date", "year", "month", "day",
    "week_day", "quarter", "time", "hour", "minute", "second",
})


class LookupInfo:
    """
    Parsed lookup information.
    
    Represents a parsed field lookup like 'name__icontains' or 'age__gt'.
    
    Attributes:
        field_name: The base field name (e.g., 'name', 'age')
        lookup: The lookup type (e.g., 'icontains', 'gt', 'exact')
        value: The value to compare against
        lookups: List of lookup parts for nested lookups
    
    Example:
        >>> info = parse_lookup('name__icontains', 'john')
        >>> info.field_name
        'name'
        >>> info.lookup
        'icontains'
    """
    
    __slots__ = ("field_name", "lookup", "value", "lookups")
    
    def __init__(
        self,
        field_name: str,
        lookup: str,
        value: Any,
        lookups: list[str] | None = None,
    ) -> None:
        self.field_name = field_name
        self.lookup = lookup
        self.value = value
        self.lookups = lookups or []
    
    def __repr__(self) -> str:
        return f"LookupInfo(field={self.field_name!r}, lookup={self.lookup!r}, value={self.value!r})"
    
    @property
    def full_lookup(self) -> str:
        """Return the full lookup string."""
        if self.lookup == "exact":
            return self.field_name
        return f"{self.field_name}__{self.lookup}"


def parse_lookup(key: str, value: Any, lookups: frozenset[str] | None = None) -> LookupInfo:
    """
    Parse a lookup key into field name and lookup type.
    
    Django-style lookup parsing for field__lookup=value syntax.
    
    Args:
        key: The lookup key (e.g., 'name__icontains', 'age__gt')
        value: The value to compare against
        lookups: Set of valid lookup names (default: DEFAULT_LOOKUPS)
    
    Returns:
        LookupInfo with parsed field name and lookup type
    
    Example:
        >>> parse_lookup('name', 'John')
        LookupInfo(field='name', lookup='exact', value='John')
        
        >>> parse_lookup('age__gt', 18)
        LookupInfo(field='age', lookup='gt', value=18)
        
        >>> parse_lookup('author__name__icontains', 'john')
        LookupInfo(field='author__name', lookup='icontains', value='john')
    """
    if lookups is None:
        lookups = DEFAULT_LOOKUPS
    
    parts = key.split("__")
    
    # If only one part, it's a simple exact lookup
    if len(parts) == 1:
        return LookupInfo(
            field_name=parts[0],
            lookup="exact",
            value=value,
            lookups=[],
        )
    
    # Find the lookup type from the end
    # Walk backwards to find the lookup type
    lookup_parts: list[str] = []
    field_parts: list[str] = []
    
    for i in range(len(parts) - 1, -1, -1):
        potential_lookup = "__".join(parts[i:])
        if potential_lookup in lookups and not field_parts:
            lookup_parts.insert(0, parts[i])
        else:
            field_parts.insert(0, parts[i])
    
    # If no lookup found, default to 'exact'
    if not lookup_parts:
        return LookupInfo(
            field_name="__".join(parts),
            lookup="exact",
            value=value,
            lookups=[],
        )
    
    # Handle composite lookups like 'date__year__gt'
    lookup_type = "__".join(lookup_parts) if len(lookup_parts) > 1 else lookup_parts[0]
    
    # Check if the combined lookup is valid
    if lookup_type not in lookups:
        # Try treating the last part as the lookup
        lookup_type = lookup_parts[-1]
        if lookup_type in lookups:
            # Rest are field parts
            field_parts.extend(lookup_parts[:-1])
        else:
            # Default to exact
            return LookupInfo(
                field_name="__".join(parts),
                lookup="exact",
                value=value,
                lookups=[],
            )
    
    return LookupInfo(
        field_name="__".join(field_parts),
        lookup=lookup_type,
        value=value,
        lookups=lookup_parts[:-1] if len(lookup_parts) > 1 else [],
    )


class Node:
    """
    Base class for query tree nodes.
    
    Represents a node in the query tree structure, supporting
    AND/OR combinations and negation.
    
    This is the base class for Q objects and provides the core
    tree manipulation functionality.
    
    Attributes:
        children: List of child nodes
        connector: The logical connector (AND/OR)
        negated: Whether this node is negated
    
    Example:
        >>> node = Node(connector=Connector.AND)
        >>> node.add(('name', 'John'), Connector.AND)
        >>> node.add(('age__gt', 18), Connector.AND)
    """
    
    _connector: Connector = Connector.AND
    _negated: bool = False
    
    def __init__(
        self,
        *args: Any,
        connector: Connector = Connector.AND,
        negated: bool = False,
        **kwargs: Any,
    ) -> None:
        self.children: list[Any] = []
        self._connector = connector
        self._negated = negated
        
        # Add positional arguments as children
        for arg in args:
            if isinstance(arg, Node):
                self.children.append(arg)
            elif isinstance(arg, dict):
                self.add(arg, connector)
        
        # Add keyword arguments
        if kwargs:
            self.add(kwargs, connector)
    
    def __and__(self, other: Any) -> "Node":
        """Combine with another node using AND."""
        if isinstance(other, Node):
            return self._combine(other, Connector.AND)
        return NotImplemented
    
    def __or__(self, other: Any) -> "Node":
        """Combine with another node using OR."""
        if isinstance(other, Node):
            return self._combine(other, Connector.OR)
        return NotImplemented
    
    def __invert__(self) -> "Node":
        """Negate this node."""
        obj = self.__class__.__new__(self.__class__)
        obj.__dict__.update(self.__dict__)
        obj._negated = not obj._negated
        return obj
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.children}, connector={self._connector.name}, negated={self._negated}>"
    
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Node):
            return (
                self.children == other.children
                and self._connector == other._connector
                and self._negated == other._negated
            )
        return False
    
    def __hash__(self) -> int:
        return hash((tuple(self.children), self._connector, self._negated))
    
    def __bool__(self) -> bool:
        """Return True if this node has children."""
        return bool(self.children)
    
    def __len__(self) -> int:
        """Return the number of children."""
        return len(self.children)
    
    def __iter__(self) -> Iterator[Any]:
        """Iterate over children."""
        return iter(self.children)
    
    def _combine(self, other: "Node", connector: Connector) -> "Node":
        """
        Combine two nodes with a connector.
        
        Creates a new node with both nodes as children.
        """
        if not self.children:
            combined = other.__class__.__new__(other.__class__)
            combined.__dict__.update(other.__dict__)
            combined._connector = connector
            return combined
        
        if not other.children:
            combined = self.__class__.__new__(self.__class__)
            combined.__dict__.update(self.__dict__)
            combined._connector = connector
            return combined
        
        combined = self.__class__(connector=connector)
        combined.add(self, connector)
        combined.add(other, connector)
        return combined
    
    def add(self, data: Any, connector: Connector) -> None:
        """
        Add data to this node.
        
        Args:
            data: Can be a Node, dict, or tuple of (key, value)
            connector: How to connect to existing children
        
        Example:
            >>> node.add({'name': 'John'}, Connector.AND)
            >>> node.add(Q(age__gt=18), Connector.OR)
        """
        # If connector differs from current, create a new branch
        if self._connector != connector and self.children:
            # Create a new child with existing children
            new_child = self.__class__(connector=self._connector, negated=self._negated)
            new_child.children = self.children
            self.children = [new_child]
            self._connector = connector
            self._negated = False
        
        if isinstance(data, Node):
            self.children.append(data)
        elif isinstance(data, dict):
            for key, value in data.items():
                self.children.append((key, value))
        elif isinstance(data, tuple) and len(data) == 2:
            self.children.append(data)
        elif isinstance(data, Iterable) and not isinstance(data, str):
            # Handle list/tuple of tuples
            for item in data:
                if isinstance(item, tuple) and len(item) == 2:
                    self.children.append(item)
    
    def combine(self, other: "Node", connector: Connector) -> "Node":
        """
        Combine this node with another using the given connector.
        
        This is an alias for _combine that modifies self in place.
        """
        if not other.children:
            return self
        
        if not self.children:
            self.__dict__.update(other.__dict__)
            return self
        
        # Create new combined node
        combined = self.__class__(connector=connector)
        combined.add(self, connector)
        combined.add(other, connector)
        
        # Update self
        self.children = combined.children
        self._connector = combined._connector
        self._negated = combined._negated
        
        return self
    
    @property
    def connector(self) -> Connector:
        """Get the connector for this node."""
        return self._connector
    
    @connector.setter
    def connector(self, value: Connector) -> None:
        """Set the connector for this node."""
        self._connector = value
    
    @property
    def negated(self) -> bool:
        """Get whether this node is negated."""
        return self._negated
    
    @negated.setter
    def negated(self, value: bool) -> None:
        """Set whether this node is negated."""
        self._negated = value
    
    def is_leaf(self) -> bool:
        """Check if this node is a leaf (has no Node children)."""
        return all(not isinstance(child, Node) for child in self.children)
    
    def flatten(self) -> list[Any]:
        """
        Flatten the node tree into a list of conditions.
        
        Returns a list of (key, value) tuples from all leaf conditions.
        """
        conditions: list[Any] = []
        for child in self.children:
            if isinstance(child, Node):
                conditions.extend(child.flatten())
            else:
                conditions.append(child)
        return conditions
    
    def copy(self) -> "Node":
        """Create a deep copy of this node."""
        obj = self.__class__.__new__(self.__class__)
        obj._connector = self._connector
        obj._negated = self._negated
        obj.children = []
        
        for child in self.children:
            if isinstance(child, Node):
                obj.children.append(child.copy())
            else:
                obj.children.append(child)
        
        return obj


def get_lookup_name(key: str) -> tuple[str, str]:
    """
    Extract field name and lookup from a key.
    
    Simple helper for common cases.
    
    Args:
        key: The lookup key
    
    Returns:
        Tuple of (field_name, lookup)
    
    Example:
        >>> get_lookup_name('name__icontains')
        ('name', 'icontains')
        >>> get_lookup_name('age')
        ('age', 'exact')
    """
    parts = key.rsplit("__", 1)
    if len(parts) == 2 and parts[1] in DEFAULT_LOOKUPS:
        return parts[0], parts[1]
    return key, "exact"


def register_lookup(lookup_name: str) -> None:
    """
    Register a new lookup type.
    
    Allows extending the ORM with custom lookup types.
    
    Args:
        lookup_name: Name of the lookup to register
    """
    global DEFAULT_LOOKUPS
    DEFAULT_LOOKUPS = frozenset(DEFAULT_LOOKUPS | {lookup_name})
