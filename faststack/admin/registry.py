"""
FastStack Admin Registry

Provides model registration and introspection for the admin panel.
"""

from dataclasses import dataclass, field
from typing import Any, Callable

from sqlmodel import SQLModel
from pydantic import BaseModel


@dataclass
class ColumnInfo:
    """Information about a model column."""

    name: str
    type: str
    required: bool
    primary_key: bool
    default: Any = None
    choices: list[tuple[str, str]] | None = None
    help_text: str | None = None
    editable: bool = True
    list_display: bool = True


@dataclass
class ModelAdmin:
    """
    Configuration for a model's admin interface.

    Attributes:
        model: The SQLModel class
        name: Display name for the model
        name_plural: Plural display name
        list_display: Columns to display in list view
        list_filter: Columns that can be filtered
        search_fields: Fields to search in
        ordering: Default ordering
        readonly_fields: Fields that cannot be edited
        exclude: Fields to exclude from forms
        list_per_page: Number of items per page
        actions: Custom admin actions
    """

    model: type[SQLModel]
    name: str = ""
    name_plural: str = ""
    list_display: list[str] = field(default_factory=lambda: ["id"])
    list_filter: list[str] = field(default_factory=list)
    search_fields: list[str] = field(default_factory=list)
    ordering: list[str] = field(default_factory=list)
    readonly_fields: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    list_per_page: int = 20
    actions: dict[str, Callable] = field(default_factory=dict)
    icon: str = "database"

    def __post_init__(self):
        """Set default names from model if not provided."""
        if not self.name:
            self.name = self.model.__name__

        if not self.name_plural:
            # Simple pluralization
            if self.name.endswith("y"):
                self.name_plural = self.name[:-1] + "ies"
            elif self.name.endswith(("s", "sh", "ch", "x", "z")):
                self.name_plural = self.name + "es"
            else:
                self.name_plural = self.name + "s"

        # Default list display to id and string representation
        if self.list_display == ["id"]:
            self.list_display = ["id", "__str__"]

    def get_columns(self) -> list[ColumnInfo]:
        """Get column information for the model."""
        columns = []

        if hasattr(self.model, "model_fields"):
            for name, field_info in self.model.model_fields.items():
                if name in self.exclude:
                    continue

                # Determine type
                field_type = "text"
                if hasattr(field_info, "annotation"):
                    annotation = field_info.annotation
                    if annotation == int or annotation == int | None:
                        field_type = "number"
                    elif annotation == float or annotation == float | None:
                        field_type = "number"
                    elif annotation == bool or annotation == bool | None:
                        field_type = "checkbox"
                    elif annotation == str or annotation == str | None:
                        field_type = "text"

                columns.append(
                    ColumnInfo(
                        name=name,
                        type=field_type,
                        required=field_info.is_required(),
                        primary_key=name == "id",
                        default=field_info.default,
                        editable=name not in self.readonly_fields and name != "id",
                        list_display=name in self.list_display or name == "id",
                    )
                )

        return columns

    def get_column_names(self) -> list[str]:
        """Get list of column names for display."""
        columns = []
        for col in self.list_display:
            if col == "__str__":
                columns.append(self.name)
            else:
                columns.append(col.replace("_", " ").title())
        return columns


class AdminRegistry:
    """
    Central registry for admin models.

    Manages registration of models and provides access to admin configurations.
    """

    def __init__(self):
        """Initialize the registry."""
        self._models: dict[str, ModelAdmin] = {}
        self._menu_items: list[dict[str, Any]] = []

    def register(
        self,
        model: type[SQLModel],
        *,
        name: str = "",
        name_plural: str = "",
        list_display: list[str] | None = None,
        list_filter: list[str] | None = None,
        search_fields: list[str] | None = None,
        ordering: list[str] | None = None,
        readonly_fields: list[str] | None = None,
        exclude: list[str] | None = None,
        list_per_page: int = 20,
        icon: str = "database",
    ) -> ModelAdmin:
        """
        Register a model with the admin.

        Args:
            model: SQLModel class to register
            name: Display name (default: model class name)
            name_plural: Plural display name
            list_display: Columns to show in list view
            list_filter: Columns that can be filtered
            search_fields: Fields to search in
            ordering: Default ordering
            readonly_fields: Fields that cannot be edited
            exclude: Fields to exclude from forms
            list_per_page: Items per page
            icon: Icon name for menu

        Returns:
            ModelAdmin instance
        """
        model_admin = ModelAdmin(
            model=model,
            name=name,
            name_plural=name_plural,
            list_display=list_display or ["id"],
            list_filter=list_filter or [],
            search_fields=search_fields or [],
            ordering=ordering or [],
            readonly_fields=readonly_fields or [],
            exclude=exclude or [],
            list_per_page=list_per_page,
            icon=icon,
        )

        key = model.__name__.lower()
        self._models[key] = model_admin

        return model_admin

    def unregister(self, model: type[SQLModel]) -> None:
        """Unregister a model from admin."""
        key = model.__name__.lower()
        self._models.pop(key, None)

    def get_model(self, name: str) -> ModelAdmin | None:
        """Get a registered model by name."""
        return self._models.get(name.lower())

    def get_all_models(self) -> dict[str, ModelAdmin]:
        """Get all registered models."""
        return self._models

    def get_menu_items(self) -> list[dict[str, Any]]:
        """Get menu items for admin navigation."""
        items = []

        # Dashboard
        items.append(
            {
                "name": "Dashboard",
                "url": "/admin/",
                "icon": "home",
            }
        )

        # Registered models
        for key, model_admin in self._models.items():
            items.append(
                {
                    "name": model_admin.name_plural,
                    "url": f"/admin/{key}/",
                    "icon": model_admin.icon,
                }
            )

        return items


# Global registry instance
admin_registry = AdminRegistry()


def register_model(
    model: type[SQLModel],
    **kwargs: Any,
) -> ModelAdmin:
    """
    Convenience function to register a model with admin.

    Args:
        model: SQLModel class to register
        **kwargs: Additional ModelAdmin options

    Returns:
        ModelAdmin instance
    """
    return admin_registry.register(model, **kwargs)
