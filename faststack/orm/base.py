"""
FastStack ORM Base Models

Provides base model classes with common fields and mixins
for SQLModel-based database models.

Features:
- Auto-incrementing primary key
- Timestamp fields
- Version field for optimistic locking
- Soft delete support
"""

from datetime import datetime
from typing import Any, ClassVar

from pydantic import field_validator
from sqlmodel import Field, SQLModel

from faststack.config import settings


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamps.

    These fields are automatically set on creation and updated on save.
    """

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class BaseModel(SQLModel):
    """
    Base model class for all FastStack models.

    Provides:
    - Auto-incrementing primary key (id)
    - Version field for optimistic locking (optional)
    - Table name convention based on class name
    - Common methods for model manipulation

    Example:
        class Item(BaseModel, table=True):
            name: str
            price: float
    """

    id: int | None = Field(default=None, primary_key=True)
    
    # Version field for optimistic locking (only used if ADMIN_OPTIMISTIC_LOCKING is enabled)
    version: int = Field(default=1, sa_column_kwargs={"server_default": "1"})

    # Class variable to control table name generation
    _table_name: ClassVar[str | None] = None
    
    # Control whether version field should be included
    _enable_versioning: ClassVar[bool] = True

    @classmethod
    def get_table_name(cls) -> str:
        """
        Get the table name for this model.

        Returns:
            Table name (lowercase class name with 's' suffix)
        """
        if cls._table_name:
            return cls._table_name

        # Convert CamelCase to snake_case and pluralize
        name = cls.__name__
        snake_case = "".join(
            ["_" + c.lower() if c.isupper() else c for c in name]
        ).lstrip("_")

        # Simple pluralization
        if snake_case.endswith("y"):
            return snake_case[:-1] + "ies"
        elif snake_case.endswith(("s", "sh", "ch", "x", "z")):
            return snake_case + "es"
        else:
            return snake_case + "s"

    @classmethod
    def get_by_id(cls, session, id: int) -> "BaseModel | None":
        """
        Get a model instance by ID.

        Args:
            session: Database session
            id: Primary key value

        Returns:
            Model instance or None if not found
        """
        return session.get(cls, id)

    def update_from_dict(self, data: dict[str, Any]) -> "BaseModel":
        """
        Update model fields from a dictionary.

        Args:
            data: Dictionary with field values to update

        Returns:
            Self for method chaining
        """
        for key, value in data.items():
            if hasattr(self, key) and key != "id":
                setattr(self, key, value)
        return self

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model to dictionary.

        Returns:
            Dictionary representation of the model
        """
        return self.model_dump()
    
    def increment_version(self) -> None:
        """
        Increment the version for optimistic locking.
        Called automatically when saving with optimistic locking enabled.
        """
        self.version = (self.version or 0) + 1
    
    def check_version(self, expected_version: int) -> bool:
        """
        Check if the current version matches expected version.
        
        Args:
            expected_version: Expected version number
        
        Returns:
            True if versions match
        """
        return self.version == expected_version
    
    def get_version_dict(self) -> dict[str, Any]:
        """
        Get a dictionary with version info for form rendering.
        
        Returns:
            Dictionary with version field
        """
        return {"_version": self.version} if settings.ADMIN_OPTIMISTIC_LOCKING else {}

    class Config:
        from_attributes = True


class TimestampedModel(BaseModel, TimestampMixin):
    """
    Base model with automatic timestamps.

    Combines BaseModel with TimestampMixin for models that
    need created_at and updated_at fields.

    Example:
        class Article(TimestampedModel, table=True):
            title: str
            content: str
    """

    pass


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.

    Instead of actually deleting records, sets is_deleted to True.
    """

    is_deleted: bool = Field(default=False)
    deleted_at: datetime | None = Field(default=None)

    def soft_delete(self) -> None:
        """Mark the record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class ActiveMixin:
    """
    Mixin for active/inactive status.

    Useful for models that can be enabled/disabled.
    """

    is_active: bool = Field(default=True)

    def activate(self) -> None:
        """Activate the record."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate the record."""
        self.is_active = False


class SluggableMixin:
    """
    Mixin for models with URL-friendly slugs.

    Auto-generates slugs from a name field.
    """

    slug: str = Field(unique=True, index=True)

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug(cls, v: str | None, info) -> str:
        """Generate slug from name if not provided."""
        if v:
            return v.lower().replace(" ", "-").replace("_", "-")

        if "name" in info.data:
            return info.data["name"].lower().replace(" ", "-").replace("_", "-")

        return v

    @staticmethod
    def slugify(text: str) -> str:
        """
        Convert text to URL-friendly slug.

        Args:
            text: Text to convert

        Returns:
            URL-friendly slug
        """
        import re

        # Convert to lowercase
        text = text.lower()
        # Replace spaces and underscores with hyphens
        text = text.replace(" ", "-").replace("_", "-")
        # Remove non-alphanumeric characters except hyphens
        text = re.sub(r"[^a-z0-9-]", "", text)
        # Remove consecutive hyphens
        text = re.sub(r"-+", "-", text)
        # Remove leading/trailing hyphens
        text = text.strip("-")

        return text
