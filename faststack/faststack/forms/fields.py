"""
Form Fields

Provides field classes for form validation and rendering.
"""

from typing import Any, Callable
from datetime import date, datetime
import re


class ValidationError(Exception):
    """Raised when field validation fails."""
    pass


class Field:
    """
    Base field class for form fields.
    
    Provides validation, cleaning, and rendering functionality.
    """
    
    def __init__(
        self,
        required: bool = True,
        label: str | None = None,
        help_text: str = "",
        initial: Any = None,
        validators: list[Callable] | None = None,
    ):
        self.required = required
        self.label = label
        self.help_text = help_text
        self.initial = initial
        self.validators = validators or []
        self.name = None
        self._errors: list[str] = []
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """
        Validate the field value.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        self._errors = []
        
        # Check required
        if self.required and (value is None or value == ""):
            return False, "This field is required"
        
        # Run custom validators
        for validator in self.validators:
            try:
                validator(value)
            except ValidationError as e:
                self._errors.append(str(e))
        
        if self._errors:
            return False, "; ".join(self._errors)
        
        return True, ""
    
    def clean(self, value: Any) -> Any:
        """
        Clean and return the value.
        
        Args:
            value: Raw value to clean
            
        Returns:
            Cleaned value
        """
        if value is None or value == "":
            return None
        return value
    
    @property
    def errors(self) -> list[str]:
        """Get validation errors."""
        return self._errors


class CharField(Field):
    """Text input field with length validation."""
    
    def __init__(
        self,
        max_length: int | None = None,
        min_length: int | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.max_length = max_length
        self.min_length = min_length
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate char field."""
        is_valid, error = super().validate(value)
        if not is_valid:
            return is_valid, error
        
        if value is not None:
            if self.min_length is not None and len(str(value)) < self.min_length:
                return False, f"Must be at least {self.min_length} characters"
            
            if self.max_length is not None and len(str(value)) > self.max_length:
                return False, f"Must be at most {self.max_length} characters"
        
        return True, ""
    
    def clean(self, value: Any) -> str | None:
        """Clean and return string value."""
        if value is None or value == "":
            return None
        return str(value).strip()


class EmailField(CharField):
    """Email input field with validation."""
    
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate email field."""
        is_valid, error = super().validate(value)
        if not is_valid:
            return is_valid, error
        
        if value is not None and not self.EMAIL_REGEX.match(str(value)):
            return False, "Enter a valid email address"
        
        return True, ""


class IntegerField(Field):
    """Integer input field with range validation."""
    
    def __init__(
        self,
        min_value: int | None = None,
        max_value: int | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate integer field."""
        is_valid, error = super().validate(value)
        if not is_valid:
            return is_valid, error
        
        if value is not None:
            try:
                int_value = int(value)
            except (ValueError, TypeError):
                return False, "Enter a valid integer"
            
            if self.min_value is not None and int_value < self.min_value:
                return False, f"Must be at least {self.min_value}"
            
            if self.max_value is not None and int_value > self.max_value:
                return False, f"Must be at most {self.max_value}"
        
        return True, ""
    
    def clean(self, value: Any) -> int | None:
        """Clean and return integer value."""
        if value is None or value == "":
            return None
        return int(value)


class FloatField(Field):
    """Float input field with range validation."""
    
    def __init__(
        self,
        min_value: float | None = None,
        max_value: float | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate float field."""
        is_valid, error = super().validate(value)
        if not is_valid:
            return is_valid, error
        
        if value is not None:
            try:
                float_value = float(value)
            except (ValueError, TypeError):
                return False, "Enter a valid number"
            
            if self.min_value is not None and float_value < self.min_value:
                return False, f"Must be at least {self.min_value}"
            
            if self.max_value is not None and float_value > self.max_value:
                return False, f"Must be at most {self.max_value}"
        
        return True, ""
    
    def clean(self, value: Any) -> float | None:
        """Clean and return float value."""
        if value is None or value == "":
            return None
        return float(value)


class BooleanField(Field):
    """Boolean checkbox field."""
    
    def __init__(self, **kwargs):
        # Boolean fields are not required by default
        kwargs.setdefault('required', False)
        super().__init__(**kwargs)
    
    def clean(self, value: Any) -> bool:
        """Clean and return boolean value."""
        if value is None or value == "":
            return False
        return bool(value)


class ChoiceField(Field):
    """Select dropdown field with choices."""
    
    def __init__(
        self,
        choices: list[tuple[str, str]] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.choices = choices or []
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate choice field."""
        is_valid, error = super().validate(value)
        if not is_valid:
            return is_valid, error
        
        if value is not None:
            valid_values = [c[0] for c in self.choices]
            if str(value) not in valid_values:
                return False, "Select a valid choice"
        
        return True, ""


class DateField(Field):
    """Date input field."""
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate date field."""
        is_valid, error = super().validate(value)
        if not is_valid:
            return is_valid, error
        
        if value is not None and not isinstance(value, (date, datetime)):
            try:
                # Try to parse date string
                if isinstance(value, str):
                    datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return False, "Enter a valid date (YYYY-MM-DD)"
        
        return True, ""
    
    def clean(self, value: Any) -> date | None:
        """Clean and return date value."""
        if value is None or value == "":
            return None
        
        if isinstance(value, date):
            return value
        
        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d").date()
        
        return None


class DateTimeField(Field):
    """DateTime input field."""
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate datetime field."""
        is_valid, error = super().validate(value)
        if not is_valid:
            return is_valid, error
        
        if value is not None and not isinstance(value, datetime):
            try:
                if isinstance(value, str):
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return False, "Enter a valid datetime"
        
        return True, ""
    
    def clean(self, value: Any) -> datetime | None:
        """Clean and return datetime value."""
        if value is None or value == "":
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        
        return None


class FileField(Field):
    """File upload field."""
    
    def __init__(
        self,
        max_size: int | None = None,
        allowed_extensions: list[str] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.max_size = max_size
        self.allowed_extensions = allowed_extensions or []
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate file field."""
        is_valid, error = super().validate(value)
        if not is_valid:
            return is_valid, error
        
        if value is not None:
            # Check file size if provided
            if self.max_size is not None and hasattr(value, 'size'):
                if value.size > self.max_size:
                    return False, f"File size must be at most {self.max_size} bytes"
            
            # Check extension if provided
            if self.allowed_extensions and hasattr(value, 'name'):
                ext = value.name.rsplit('.', 1)[-1].lower()
                if ext not in [e.lower() for e in self.allowed_extensions]:
                    return False, f"File extension must be one of: {', '.join(self.allowed_extensions)}"
        
        return True, ""


class HiddenField(Field):
    """Hidden input field."""
    pass


class SlugField(CharField):
    """Slug field with automatic slug validation."""
    
    SLUG_REGEX = re.compile(r'^[-a-zA-Z0-9_]+$')
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate slug field."""
        is_valid, error = super().validate(value)
        if not is_valid:
            return is_valid, error
        
        if value is not None and not self.SLUG_REGEX.match(str(value)):
            return False, "Enter a valid slug (letters, numbers, underscores, hyphens)"
        
        return True, ""


class URLField(CharField):
    """URL input field with validation."""
    
    URL_REGEX = re.compile(
        r'^(https?://)?'  # Optional http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # Domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # Optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate URL field."""
        is_valid, error = super().validate(value)
        if not is_valid:
            return is_valid, error
        
        if value is not None and not self.URL_REGEX.match(str(value)):
            return False, "Enter a valid URL"
        
        return True, ""


class PasswordField(CharField):
    """Password input field (renders as password input)."""
    pass


class TextField(CharField):
    """Textarea field for long text."""
    pass
