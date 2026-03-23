"""
Tests for FastStack Forms

Tests form validation, fields, widgets, and form processing.
"""

import pytest
from datetime import datetime, date
from unittest.mock import MagicMock


class TestFormFieldTypes:
    """Tests for form field types."""

    def test_char_field(self):
        """Test CharField validation."""
        from faststack.faststack.forms.fields import CharField
        
        field = CharField(required=True, min_length=2, max_length=10)
        
        # Valid value
        is_valid, error = field.validate("test")
        assert is_valid is True
        
        # Too short
        is_valid, error = field.validate("a")
        assert is_valid is False
        
        # Too long
        is_valid, error = field.validate("a" * 15)
        assert is_valid is False
        
        # Missing required
        is_valid, error = field.validate(None)
        assert is_valid is False

    def test_integer_field(self):
        """Test IntegerField validation."""
        from faststack.faststack.forms.fields import IntegerField
        
        field = IntegerField(required=True, min_value=0, max_value=100)
        
        # Valid value
        is_valid, error = field.validate(50)
        assert is_valid is True
        
        # Too small
        is_valid, error = field.validate(-1)
        assert is_valid is False
        
        # Too large
        is_valid, error = field.validate(101)
        assert is_valid is False

    def test_email_field(self):
        """Test EmailField validation."""
        from faststack.faststack.forms.fields import EmailField
        
        field = EmailField(required=True)
        
        # Valid email
        is_valid, error = field.validate("test@example.com")
        assert is_valid is True
        
        # Invalid email
        is_valid, error = field.validate("invalid-email")
        assert is_valid is False

    def test_boolean_field(self):
        """Test BooleanField validation."""
        from faststack.faststack.forms.fields import BooleanField
        
        field = BooleanField(required=False)
        
        # Valid values
        is_valid, error = field.validate(True)
        assert is_valid is True
        
        is_valid, error = field.validate(False)
        assert is_valid is True

    def test_date_field(self):
        """Test DateField validation."""
        from faststack.faststack.forms.fields import DateField
        
        field = DateField(required=True)
        
        # Valid date
        is_valid, error = field.validate(date(2024, 1, 1))
        assert is_valid is True

    def test_choice_field(self):
        """Test ChoiceField validation."""
        from faststack.faststack.forms.fields import ChoiceField
        
        field = ChoiceField(
            required=True,
            choices=[("a", "Option A"), ("b", "Option B")]
        )
        
        # Valid choice
        is_valid, error = field.validate("a")
        assert is_valid is True
        
        # Invalid choice
        is_valid, error = field.validate("c")
        assert is_valid is False


class TestFormWidgets:
    """Tests for form widgets."""

    def test_text_input_widget(self):
        """Test TextInput widget rendering."""
        from faststack.faststack.forms.widgets import TextInput
        
        widget = TextInput(attrs={"class": "form-control"})
        
        html = widget.render("name", "value")
        
        assert 'type="text"' in html
        assert 'name="name"' in html
        assert 'value="value"' in html
        assert 'class="form-control"' in html

    def test_password_input_widget(self):
        """Test PasswordInput widget rendering."""
        from faststack.faststack.forms.widgets import PasswordInput
        
        widget = PasswordInput()
        
        html = widget.render("password", "")
        
        assert 'type="password"' in html
        assert 'name="password"' in html

    def test_email_input_widget(self):
        """Test EmailInput widget rendering."""
        from faststack.faststack.forms.widgets import EmailInput
        
        widget = EmailInput()
        
        html = widget.render("email", "test@example.com")
        
        assert 'type="email"' in html

    def test_textarea_widget(self):
        """Test Textarea widget rendering."""
        from faststack.faststack.forms.widgets import Textarea
        
        widget = Textarea()
        
        html = widget.render("content", "Some content")
        
        assert "<textarea" in html
        assert "</textarea>" in html
        assert "Some content" in html

    def test_select_widget(self):
        """Test Select widget rendering."""
        from faststack.faststack.forms.widgets import Select
        
        widget = Select(choices=[("a", "A"), ("b", "B")])
        
        html = widget.render("choice", "a")
        
        assert "<select" in html
        assert "</select>" in html
        assert '<option value="a"' in html
        assert "selected" in html  # 'a' should be selected

    def test_checkbox_input_widget(self):
        """Test CheckboxInput widget rendering."""
        from faststack.faststack.forms.widgets import CheckboxInput
        
        widget = CheckboxInput()
        
        # Checked
        html = widget.render("agree", True)
        assert 'type="checkbox"' in html
        assert "checked" in html
        
        # Unchecked
        html = widget.render("agree", False)
        assert "checked" not in html


class TestFormValidation:
    """Tests for form validation."""

    def test_form_is_valid(self):
        """Test form validation with valid data."""
        from faststack.faststack.forms.forms import Form
        from faststack.faststack.forms.fields import CharField, EmailField
        
        class TestForm(Form):
            name = CharField(required=True)
            email = EmailField(required=True)
        
        form = TestForm(data={"name": "Test", "email": "test@example.com"})
        
        is_valid = form.is_valid()
        
        assert is_valid is True
        assert form.errors == {}

    def test_form_is_invalid(self):
        """Test form validation with invalid data."""
        from faststack.faststack.forms.forms import Form
        from faststack.faststack.forms.fields import CharField, EmailField
        
        class TestForm(Form):
            name = CharField(required=True)
            email = EmailField(required=True)
        
        form = TestForm(data={"name": "", "email": "invalid"})
        
        is_valid = form.is_valid()
        
        assert is_valid is False
        assert len(form.errors) > 0

    def test_form_cleaned_data(self):
        """Test accessing cleaned data after validation."""
        from faststack.faststack.forms.forms import Form
        from faststack.faststack.forms.fields import CharField, IntegerField
        
        class TestForm(Form):
            name = CharField(required=True)
            age = IntegerField(required=True)
        
        form = TestForm(data={"name": "Test", "age": "25"})
        form.is_valid()
        
        assert form.cleaned_data["name"] == "Test"
        assert form.cleaned_data["age"] == 25

    def test_form_missing_required_field(self):
        """Test form with missing required field."""
        from faststack.faststack.forms.forms import Form
        from faststack.faststack.forms.fields import CharField
        
        class TestForm(Form):
            name = CharField(required=True)
        
        form = TestForm(data={})
        
        assert form.is_valid() is False
        assert "name" in form.errors


class TestFormValidators:
    """Tests for form validators."""

    def test_required_validator(self):
        """Test required validator."""
        from faststack.faststack.forms.validators import RequiredValidator
        
        validator = RequiredValidator()
        
        # Value present
        is_valid, error = validator.validate("value")
        assert is_valid is True
        
        # Empty value
        is_valid, error = validator.validate("")
        assert is_valid is False

    def test_min_length_validator(self):
        """Test min length validator."""
        from faststack.faststack.forms.validators import MinLengthValidator
        
        validator = MinLengthValidator(min_length=3)
        
        # Valid
        is_valid, error = validator.validate("test")
        assert is_valid is True
        
        # Too short
        is_valid, error = validator.validate("ab")
        assert is_valid is False

    def test_max_length_validator(self):
        """Test max length validator."""
        from faststack.faststack.forms.validators import MaxLengthValidator
        
        validator = MaxLengthValidator(max_length=10)
        
        # Valid
        is_valid, error = validator.validate("test")
        assert is_valid is True
        
        # Too long
        is_valid, error = validator.validate("a" * 15)
        assert is_valid is False

    def test_regex_validator(self):
        """Test regex validator."""
        from faststack.faststack.forms.validators import RegexValidator
        
        validator = RegexValidator(pattern=r"^\d+$", message="Must be digits only")
        
        # Valid
        is_valid, error = validator.validate("12345")
        assert is_valid is True
        
        # Invalid
        is_valid, error = validator.validate("abc")
        assert is_valid is False


class TestModelForm:
    """Tests for ModelForm functionality."""

    def test_model_form_creation(self):
        """Test creating a ModelForm from a model."""
        from faststack.faststack.forms.forms import ModelForm
        from faststack.orm.base import BaseModel
        from sqlmodel import Field
        
        class TestModel(BaseModel, table=True):
            __tablename__ = "test_model"
            name: str = Field(default="")
            email: str = Field(default="")
        
        class TestModelForm(ModelForm):
            class Meta:
                model = TestModel
                fields = ["name", "email"]
        
        form = TestModelForm()
        
        assert "name" in form.fields
        assert "email" in form.fields
