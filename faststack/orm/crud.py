"""
FastStack CRUD Helpers

Provides generic CRUD (Create, Read, Update, Delete) operations
for SQLModel models, reducing boilerplate code.
"""

from typing import Any, Generic, TypeVar
from collections.abc import Sequence

from pydantic import BaseModel as PydanticModel
from sqlmodel import Session, SQLModel, select, func, col

from faststack.orm.base import BaseModel as FastStackBaseModel

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=PydanticModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=PydanticModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base CRUD class with generic operations.

    Provides standard CRUD operations for any SQLModel model.
    Can be extended with custom methods for specific models.

    Example:
        class ItemCRUD(CRUDBase[Item, ItemCreate, ItemUpdate]):
            def get_by_name(self, session: Session, name: str) -> Item | None:
                return session.exec(select(Item).where(Item.name == name)).first()

        item_crud = ItemCRUD(Item)
    """

    def __init__(self, model: type[ModelType]):
        """
        Initialize CRUD with a model class.

        Args:
            model: The SQLModel class to perform CRUD on
        """
        self.model = model

    def get(self, session: Session, id: int) -> ModelType | None:
        """
        Get a single record by ID.

        Args:
            session: Database session
            id: Primary key value

        Returns:
            Model instance or None if not found
        """
        return session.get(self.model, id)

    def get_multi(
        self,
        session: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Any = None,
        descending: bool = False,
    ) -> list[ModelType]:
        """
        Get multiple records with pagination.

        Args:
            session: Database session
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            order_by: Column to order by (default: id)
            descending: If True, order in descending order

        Returns:
            List of model instances
        """
        statement = select(self.model)

        if order_by is not None:
            if descending:
                statement = statement.order_by(order_by.desc())
            else:
                statement = statement.order_by(order_by)
        elif hasattr(self.model, "id"):
            statement = statement.order_by(self.model.id)

        statement = statement.offset(skip).limit(limit)

        return list(session.exec(statement).all())

    def get_all(self, session: Session) -> list[ModelType]:
        """
        Get all records.

        Args:
            session: Database session

        Returns:
            List of all model instances
        """
        return list(session.exec(select(self.model)).all())

    def create(
        self, session: Session, *, obj_in: CreateSchemaType | dict[str, Any]
    ) -> ModelType:
        """
        Create a new record.

        Args:
            session: Database session
            obj_in: Creation data (Pydantic model or dict)

        Returns:
            Created model instance
        """
        if isinstance(obj_in, dict):
            obj_data = obj_in
        else:
            obj_data = obj_in.model_dump(exclude_unset=True)

        db_obj = self.model(**obj_data)
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)

        return db_obj

    def update(
        self,
        session: Session,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """
        Update an existing record.

        Args:
            session: Database session
            db_obj: Existing model instance to update
            obj_in: Update data (Pydantic model or dict)

        Returns:
            Updated model instance
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        # Update timestamp if available
        if hasattr(db_obj, "touch"):
            db_obj.touch()

        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)

        return db_obj

    def delete(self, session: Session, *, id: int) -> ModelType | None:
        """
        Delete a record by ID.

        Args:
            session: Database session
            id: Primary key value

        Returns:
            Deleted model instance or None if not found
        """
        obj = session.get(self.model, id)
        if obj:
            session.delete(obj)
            session.commit()
        return obj

    def soft_delete(self, session: Session, *, id: int) -> ModelType | None:
        """
        Soft delete a record by ID.

        Only works if model has SoftDeleteMixin.

        Args:
            session: Database session
            id: Primary key value

        Returns:
            Soft-deleted model instance or None if not found
        """
        obj = session.get(self.model, id)
        if obj and hasattr(obj, "soft_delete"):
            obj.soft_delete()
            session.add(obj)
            session.commit()
            session.refresh(obj)
        return obj

    def count(self, session: Session, **filters) -> int:
        """
        Count records matching filters.

        Args:
            session: Database session
            **filters: Field=value pairs to filter by

        Returns:
            Number of matching records
        """
        statement = select(func.count()).select_from(self.model)

        for field, value in filters.items():
            if hasattr(self.model, field):
                statement = statement.where(getattr(self.model, field) == value)

        return session.exec(statement).one()

    def exists(self, session: Session, id: int) -> bool:
        """
        Check if a record exists.

        Args:
            session: Database session
            id: Primary key value

        Returns:
            True if record exists, False otherwise
        """
        return session.get(self.model, id) is not None

    def search(
        self,
        session: Session,
        *,
        field: str,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """
        Search records by a field with partial match.

        Args:
            session: Database session
            field: Field name to search in
            query: Search query (partial match)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching model instances
        """
        if not hasattr(self.model, field):
            return []

        column = getattr(self.model, field)
        statement = (
            select(self.model)
            .where(col(column).contains(query))
            .offset(skip)
            .limit(limit)
        )

        return list(session.exec(statement).all())

    def filter(
        self,
        session: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        **filters,
    ) -> list[ModelType]:
        """
        Filter records by field values.

        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Field=value pairs to filter by

        Returns:
            List of matching model instances
        """
        statement = select(self.model)

        for field, value in filters.items():
            if hasattr(self.model, field):
                statement = statement.where(getattr(self.model, field) == value)

        statement = statement.offset(skip).limit(limit)

        return list(session.exec(statement).all())

    def get_or_create(
        self,
        session: Session,
        *,
        defaults: dict[str, Any] | None = None,
        **lookup,
    ) -> tuple[ModelType, bool]:
        """
        Get an existing record or create a new one.

        Args:
            session: Database session
            defaults: Default values for creation
            **lookup: Field=value pairs to look up

        Returns:
            Tuple of (model instance, created boolean)
        """
        # Try to find existing
        statement = select(self.model)
        for field, value in lookup.items():
            if hasattr(self.model, field):
                statement = statement.where(getattr(self.model, field) == value)

        obj = session.exec(statement).first()

        if obj:
            return obj, False

        # Create new
        create_data = {**lookup}
        if defaults:
            create_data.update(defaults)

        obj = self.create(session, obj_in=create_data)
        return obj, True


class CRUDModel(CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Extended CRUD class with additional utility methods.

    Includes advanced filtering, bulk operations, and more.
    """

    def bulk_create(
        self, session: Session, *, objs_in: list[CreateSchemaType | dict[str, Any]]
    ) -> list[ModelType]:
        """
        Create multiple records at once.

        Args:
            session: Database session
            objs_in: List of creation data

        Returns:
            List of created model instances
        """
        created = []
        for obj_in in objs_in:
            obj = self.create(session, obj_in=obj_in)
            created.append(obj)
        return created

    def bulk_update(
        self,
        session: Session,
        *,
        ids: list[int],
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> list[ModelType]:
        """
        Update multiple records at once.

        Args:
            session: Database session
            ids: List of primary key values
            obj_in: Update data to apply to all

        Returns:
            List of updated model instances
        """
        updated = []
        for id in ids:
            obj = self.get(session, id)
            if obj:
                updated.append(self.update(session, db_obj=obj, obj_in=obj_in))
        return updated

    def bulk_delete(self, session: Session, *, ids: list[int]) -> int:
        """
        Delete multiple records at once.

        Args:
            session: Database session
            ids: List of primary key values

        Returns:
            Number of records deleted
        """
        count = 0
        for id in ids:
            if self.delete(session, id=id):
                count += 1
        return count

    def get_latest(
        self, session: Session, *, limit: int = 10, field: str = "created_at"
    ) -> list[ModelType]:
        """
        Get the most recent records.

        Args:
            session: Database session
            limit: Maximum number of records to return
            field: Field to order by (default: created_at)

        Returns:
            List of most recent model instances
        """
        if not hasattr(self.model, field):
            return self.get_multi(session, limit=limit)

        column = getattr(self.model, field)
        statement = select(self.model).order_by(column.desc()).limit(limit)

        return list(session.exec(statement).all())
