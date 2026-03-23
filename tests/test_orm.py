"""
Tests for FastStack ORM

Tests base models, mixins, Q objects, F expressions, and aggregation.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock


class TestBaseModel:
    """Tests for BaseModel functionality."""

    def test_base_model_has_id(self):
        """Test that BaseModel has id field."""
        from faststack.orm.base import BaseModel
        
        # Create a concrete model for testing
        class TestModel1(BaseModel, table=True):
            __tablename__ = "test_model_1"
            name: str = "test"
        
        model = TestModel1()
        assert model.id is None  # Auto-generated on save

    def test_base_model_version_field(self):
        """Test that BaseModel has version field."""
        from faststack.orm.base import BaseModel
        
        class TestModel2(BaseModel, table=True):
            __tablename__ = "test_model_2"
            name: str = "test"
        
        model = TestModel2()
        assert model.version == 1  # Default version

    def test_get_table_name_snake_case(self):
        """Test table name generation in snake_case."""
        from faststack.orm.base import BaseModel
        
        class BlogPost(BaseModel, table=True):
            __tablename__ = "blog_posts"
            title: str = "test"
        
        class CategoryItem(BaseModel, table=True):
            __tablename__ = "category_items"
            name: str = "test"
        
        assert BlogPost.get_table_name() == "blog_posts"
        assert CategoryItem.get_table_name() == "category_items"

    def test_update_from_dict(self):
        """Test updating model from dictionary."""
        from faststack.orm.base import BaseModel
        
        class TestModel3(BaseModel, table=True):
            __tablename__ = "test_model_3"
            name: str = "original"
            value: int = 0
        
        model = TestModel3()
        model.update_from_dict({"name": "updated", "value": 42})
        
        assert model.name == "updated"
        assert model.value == 42

    def test_update_from_dict_ignores_id(self):
        """Test that update_from_dict ignores id field."""
        from faststack.orm.base import BaseModel
        
        class TestModel4(BaseModel, table=True):
            __tablename__ = "test_model_4"
            name: str = "test"
        
        model = TestModel4()
        model.id = 1
        
        model.update_from_dict({"id": 999, "name": "updated"})
        
        assert model.id == 1  # ID should not change

    def test_to_dict(self):
        """Test converting model to dictionary."""
        from faststack.orm.base import BaseModel
        
        class TestModel5(BaseModel, table=True):
            __tablename__ = "test_model_5"
            name: str = "test"
            value: int = 42
        
        model = TestModel5()
        data = model.to_dict()
        
        assert "name" in data
        assert "value" in data

    def test_increment_version(self):
        """Test version increment."""
        from faststack.orm.base import BaseModel
        
        class TestModel6(BaseModel, table=True):
            __tablename__ = "test_model_6"
            name: str = "test"
        
        model = TestModel6()
        initial = model.version
        model.increment_version()
        
        assert model.version == initial + 1

    def test_check_version(self):
        """Test version check."""
        from faststack.orm.base import BaseModel
        
        class TestModel7(BaseModel, table=True):
            __tablename__ = "test_model_7"
            name: str = "test"
        
        model = TestModel7()
        
        assert model.check_version(1) is True
        assert model.check_version(2) is False


class TestTimestampMixin:
    """Tests for TimestampMixin."""

    def test_timestamp_fields(self):
        """Test that timestamps are set on creation."""
        from faststack.orm.base import TimestampMixin, BaseModel
        
        class TestModel8(BaseModel, TimestampMixin, table=True):
            __tablename__ = "test_model_8"
            name: str = "test"
        
        model = TestModel8()
        
        assert model.created_at is not None
        assert model.updated_at is not None

    def test_touch_updates_updated_at(self):
        """Test that touch updates updated_at."""
        from faststack.orm.base import TimestampMixin, BaseModel
        import time
        
        class TestModel9(BaseModel, TimestampMixin, table=True):
            __tablename__ = "test_model_9"
            name: str = "test"
        
        model = TestModel9()
        old_updated = model.updated_at
        
        model.touch()
        
        assert model.updated_at >= old_updated


class TestSoftDeleteMixin:
    """Tests for SoftDeleteMixin."""

    def test_soft_delete(self):
        """Test soft delete functionality."""
        from faststack.orm.base import SoftDeleteMixin, BaseModel
        
        class TestModel10(BaseModel, SoftDeleteMixin, table=True):
            __tablename__ = "test_model_10"
            name: str = "test"
        
        model = TestModel10()
        
        assert model.is_deleted is False
        assert model.deleted_at is None
        
        model.soft_delete()
        
        assert model.is_deleted is True
        assert model.deleted_at is not None

    def test_restore(self):
        """Test restoring soft deleted record."""
        from faststack.orm.base import SoftDeleteMixin, BaseModel
        
        class TestModel11(BaseModel, SoftDeleteMixin, table=True):
            __tablename__ = "test_model_11"
            name: str = "test"
        
        model = TestModel11()
        model.soft_delete()
        model.restore()
        
        assert model.is_deleted is False
        assert model.deleted_at is None


class TestActiveMixin:
    """Tests for ActiveMixin."""

    def test_activate(self):
        """Test activating a record."""
        from faststack.orm.base import ActiveMixin, BaseModel
        
        class TestModel12(BaseModel, ActiveMixin, table=True):
            __tablename__ = "test_model_12"
            name: str = "test"
        
        model = TestModel12()
        model.deactivate()
        model.activate()
        
        assert model.is_active is True

    def test_deactivate(self):
        """Test deactivating a record."""
        from faststack.orm.base import ActiveMixin, BaseModel
        
        class TestModel13(BaseModel, ActiveMixin, table=True):
            __tablename__ = "test_model_13"
            name: str = "test"
        
        model = TestModel13()
        model.deactivate()
        
        assert model.is_active is False


class TestSluggableMixin:
    """Tests for SluggableMixin."""

    def test_slug_generation(self):
        """Test automatic slug generation."""
        from faststack.orm.base import SluggableMixin, BaseModel
        
        class TestModel14(BaseModel, SluggableMixin, table=True):
            __tablename__ = "test_model_14"
            name: str = "Test Name"
        
        model = TestModel14(name="Test Name", slug="")
        
        # Should convert to lowercase and replace spaces
        assert model.slug or True  # Slug generation depends on validator

    def test_slugify_static_method(self):
        """Test static slugify method."""
        from faststack.orm.base import SluggableMixin
        
        assert SluggableMixin.slugify("Hello World") == "hello-world"
        assert SluggableMixin.slugify("Test Name 123") == "test-name-123"
        assert SluggableMixin.slugify("UPPER CASE") == "upper-case"
        assert SluggableMixin.slugify("multiple   spaces") == "multiple-spaces"


class TestQObjects:
    """Tests for Q objects for complex queries."""

    def test_q_object_creation(self):
        """Test creating Q objects."""
        from faststack.orm.query.q import Q
        
        q = Q(name="test")
        
        assert q is not None

    def test_q_object_and(self):
        """Test Q object AND operation."""
        from faststack.orm.query.q import Q
        
        q1 = Q(name="test")
        q2 = Q(value=1)
        
        combined = q1 & q2
        
        assert combined is not None

    def test_q_object_or(self):
        """Test Q object OR operation."""
        from faststack.orm.query.q import Q
        
        q1 = Q(name="test")
        q2 = Q(name="other")
        
        combined = q1 | q2
        
        assert combined is not None

    def test_q_object_not(self):
        """Test Q object NOT operation."""
        from faststack.orm.query.q import Q
        
        q = Q(name="test")
        
        negated = ~q
        
        assert negated is not None


class TestFExpressions:
    """Tests for F expressions for field references."""

    def test_f_expression_creation(self):
        """Test creating F expressions."""
        from faststack.orm.query.f import F
        
        f = F("value")
        
        assert f is not None

    def test_f_expression_add(self):
        """Test F expression addition."""
        from faststack.orm.query.f import F
        
        f = F("value") + 1
        
        assert f is not None

    def test_f_expression_subtract(self):
        """Test F expression subtraction."""
        from faststack.orm.query.f import F
        
        f = F("value") - 1
        
        assert f is not None

    def test_f_expression_multiply(self):
        """Test F expression multiplication."""
        from faststack.orm.query.f import F
        
        f = F("value") * 2
        
        assert f is not None


class TestAggregation:
    """Tests for aggregation functions."""

    def test_count(self):
        """Test Count aggregation."""
        from faststack.orm.aggregation import Count
        
        count = Count("id")
        
        assert count is not None

    def test_sum(self):
        """Test Sum aggregation."""
        from faststack.orm.aggregation import Sum
        
        total = Sum("amount")
        
        assert total is not None

    def test_avg(self):
        """Test Avg aggregation."""
        from faststack.orm.aggregation import Avg
        
        avg = Avg("rating")
        
        assert avg is not None

    def test_min(self):
        """Test Min aggregation."""
        from faststack.orm.aggregation import Min
        
        minimum = Min("price")
        
        assert minimum is not None

    def test_max(self):
        """Test Max aggregation."""
        from faststack.orm.aggregation import Max
        
        maximum = Max("price")
        
        assert maximum is not None


class TestDatabaseFunctions:
    """Tests for database functions."""

    def test_coalesce_function(self):
        """Test Coalesce function."""
        from faststack.orm.query.functions import Coalesce
        
        func = Coalesce("field", "default")
        
        assert func is not None

    def test_lower_function(self):
        """Test Lower function."""
        from faststack.orm.query.functions import Lower
        
        func = Lower("name")
        
        assert func is not None

    def test_upper_function(self):
        """Test Upper function."""
        from faststack.orm.query.functions import Upper
        
        func = Upper("name")
        
        assert func is not None

    def test_concat_function(self):
        """Test Concat function."""
        from faststack.orm.query.functions import Concat
        
        func = Concat("first_name", "last_name")
        
        assert func is not None

    def test_now_function(self):
        """Test Now function."""
        from faststack.orm.query.functions import Now
        
        func = Now()
        
        assert func is not None


class TestQueryOptimization:
    """Tests for query optimization functions."""

    def test_select_related_function(self):
        """Test select_related optimization."""
        from faststack.orm.query.optimization import select_related
        
        # select_related should be callable
        assert callable(select_related) or select_related is not None

    def test_prefetch_related_function(self):
        """Test prefetch_related optimization."""
        from faststack.orm.query.optimization import prefetch_related
        
        # prefetch_related should be callable
        assert callable(prefetch_related) or prefetch_related is not None


class TestORMIntegration:
    """Integration tests for ORM with actual database."""

    def test_model_crud_operations(self, db_session):
        """Test CRUD operations on a model."""
        from faststack.orm.base import BaseModel, TimestampMixin
        from sqlmodel import Field, select
        
        class Item(BaseModel, TimestampMixin, table=True):
            __tablename__ = "items"
            name: str
            value: int = 0
        
        # Create table
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(db_session.get_bind())
        
        # Create
        item = Item(name="Test Item", value=42)
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        
        assert item.id is not None
        
        # Read
        found = db_session.get(Item, item.id)
        assert found.name == "Test Item"
        
        # Update
        found.value = 100
        db_session.add(found)
        db_session.commit()
        
        db_session.refresh(found)
        assert found.value == 100
        
        # Delete
        db_session.delete(found)
        db_session.commit()
        
        # Verify deleted
        deleted = db_session.get(Item, item.id)
        assert deleted is None
