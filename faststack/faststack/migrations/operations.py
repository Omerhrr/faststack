"""
Migration Operations

Operations that can be performed in migrations.
"""

from typing import Any, Callable


class Operation:
    """Base class for migration operations."""

    reversible = True

    @property
    def operation_type(self) -> str:
        return "Operation"

    def deconstruct(self) -> dict:
        return {"operation": self.operation_type}

    def state_forwards(self, state):
        return state

    def database_forwards(self, app_label: str, connection, state) -> list[str]:
        return []

    def database_backwards(self, app_label: str, connection, state) -> list[str]:
        raise NotImplementedError("Cannot reverse this operation")

    def describe(self) -> str:
        return f"{self.operation_type} operation"


class CreateModel(Operation):
    """Create a new model/table."""
    operation_type = "CreateModel"

    def __init__(self, name: str, fields: dict, options: dict | None = None):
        self.name = name
        self.fields = fields
        self.options = options or {}

    def deconstruct(self) -> dict:
        return {
            "operation": "CreateModel",
            "name": self.name,
            "fields": self.fields,
            "options": self.options,
        }

    def describe(self) -> str:
        return f"Create model {self.name}"


class DeleteModel(Operation):
    """Delete a model/table."""
    operation_type = "DeleteModel"

    def __init__(self, name: str):
        self.name = name

    def describe(self) -> str:
        return f"Delete model {self.name}"


class RenameModel(Operation):
    """Rename a model."""
    operation_type = "RenameModel"

    def __init__(self, old_name: str, new_name: str):
        self.old_name = old_name
        self.new_name = new_name

    def describe(self) -> str:
        return f"Rename model {self.old_name} to {self.new_name}"


class AddField(Operation):
    """Add a field to a model."""
    operation_type = "AddField"

    def __init__(self, model_name: str, name: str, field: Any):
        self.model_name = model_name
        self.name = name
        self.field = field

    def describe(self) -> str:
        return f"Add field {self.name} to {self.model_name}"


class RemoveField(Operation):
    """Remove a field from a model."""
    operation_type = "RemoveField"

    def __init__(self, model_name: str, name: str):
        self.model_name = model_name
        self.name = name

    def describe(self) -> str:
        return f"Remove field {self.name} from {self.model_name}"


class RenameField(Operation):
    """Rename a field in a model."""
    operation_type = "RenameField"

    def __init__(self, model_name: str, old_name: str, new_name: str):
        self.model_name = model_name
        self.old_name = old_name
        self.new_name = new_name

    def describe(self) -> str:
        return f"Rename field {self.old_name} to {self.new_name} in {self.model_name}"


class AlterField(Operation):
    """Alter a field's attributes."""
    operation_type = "AlterField"

    def __init__(self, model_name: str, name: str, field: Any):
        self.model_name = model_name
        self.name = name
        self.field = field

    def describe(self) -> str:
        return f"Alter field {self.name} in {self.model_name}"


class AddIndex(Operation):
    """Add an index to a model."""
    operation_type = "AddIndex"

    def __init__(self, model_name: str, index: Any):
        self.model_name = model_name
        self.index = index

    def describe(self) -> str:
        return f"Add index to {self.model_name}"


class RemoveIndex(Operation):
    """Remove an index from a model."""
    operation_type = "RemoveIndex"

    def __init__(self, model_name: str, name: str):
        self.model_name = model_name
        self.name = name

    def describe(self) -> str:
        return f"Remove index {self.name} from {self.model_name}"


class RunPython(Operation):
    """Run a Python function."""
    operation_type = "RunPython"

    def __init__(self, code: Callable, reverse_code: Callable | None = None):
        self.code = code
        self.reverse_code = reverse_code

    def describe(self) -> str:
        return f"RunPython: {self.code.__name__}"


class RunSQL(Operation):
    """Run raw SQL."""
    operation_type = "RunSQL"

    def __init__(self, sql: str | list, reverse_sql: str | list | None = None):
        self.sql = sql
        self.reverse_sql = reverse_sql

    def describe(self) -> str:
        return "RunSQL"
