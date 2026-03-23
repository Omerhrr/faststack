"""
Migration Base Class

Base class for all migrations.
"""

from typing import Any, Callable
from datetime import datetime


class Migration:
    """
    Base class for all migrations.
    
    Example:
        class Migration(Migration):
            dependencies = [
                ('auth', '0001_initial'),
            ]
            
            operations = [
                AddField('User', 'avatar', ImageField(null=True)),
            ]
    """
    
    initial = False
    dependencies: list[tuple[str, str]] = []
    operations: list[Any] = []
    app_label: str | None = None
    name: str | None = None
    
    def __init__(self, name: str | None = None, app_label: str | None = None):
        self.name = name
        self.app_label = app_label
    
    def __repr__(self) -> str:
        return f"<Migration {self.app_label}.{self.name}>"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Migration):
            return False
        return self.app_label == other.app_label and self.name == other.name
    
    def __hash__(self) -> int:
        return hash((self.app_label, self.name))
    
    def suggest_name(self) -> str:
        """Suggest a name for this migration based on operations."""
        if not self.operations:
            return "empty"
        if self.initial:
            return "initial"
        return "auto"
    
    def apply(self, state: Any, connection: Any) -> Any:
        """Apply this migration."""
        for operation in self.operations:
            state = operation.state_forwards(state)
        return state
    
    def unapply(self, state: Any, connection: Any) -> Any:
        """Unapply this migration."""
        for operation in reversed(self.operations):
            pass
        return state
