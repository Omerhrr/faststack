"""
Form Validators

Provides validator classes for form field validation.
"""

import re
from typing import Any, Callable


class ValidationError(Exception):
    """Raised when validation fails."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class Validator:
    """Base validator class."""
    
    def __call__(self, value: Any) -> None:
        """
        Validate the value.
        
        Raises:
            ValidationError: If validation fails
        """
        pass
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """
        Validate the value and return a tuple.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            self(value)
            return True, ""
        except ValidationError as e:
            return False, e.message


class RequiredValidator(Validator):
    """Validates that a value is present."""
    
    def __init__(self, message: str = "This field is required"):
        self.message = message
    
    def __call__(self, value: Any) -> None:
        if value is None or value == "" or (isinstance(value, (list, dict)) and not value):
            raise ValidationError(self.message)


class MinLengthValidator(Validator):
    """Validates minimum string length."""
    
    def __init__(self, min_length: int, message: str | None = None):
        self.min_length = min_length
        self.message = message or f"Must be at least {min_length} characters"
    
    def __call__(self, value: Any) -> None:
        if value is not None and len(str(value)) < self.min_length:
            raise ValidationError(self.message)


class MaxLengthValidator(Validator):
    """Validates maximum string length."""
    
    def __init__(self, max_length: int, message: str | None = None):
        self.max_length = max_length
        self.message = message or f"Must be at most {max_length} characters"
    
    def __call__(self, value: Any) -> None:
        if value is not None and len(str(value)) > self.max_length:
            raise ValidationError(self.message)


class EmailValidator(Validator):
    """Validates email format."""
    
    pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def __init__(self, message: str = "Enter a valid email address"):
        self.message = message
    
    def __call__(self, value: Any) -> None:
        if value and not self.pattern.match(str(value)):
            raise ValidationError(self.message)


class URLValidator(Validator):
    """Validates URL format."""
    
    pattern = re.compile(
        r'^(https?://)?'  # Optional http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # Domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # Optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    def __init__(self, message: str = "Enter a valid URL"):
        self.message = message
    
    def __call__(self, value: Any) -> None:
        if value and not self.pattern.match(str(value)):
            raise ValidationError(self.message)


class RegexValidator(Validator):
    """Validates value against a regex pattern."""
    
    def __init__(
        self,
        pattern: str,
        message: str = "Enter a valid value",
        inverse_match: bool = False
    ):
        self.pattern = re.compile(pattern)
        self.message = message
        self.inverse_match = inverse_match
    
    def __call__(self, value: Any) -> None:
        if value is None:
            return
        
        match = self.pattern.match(str(value))
        if self.inverse_match:
            if match:
                raise ValidationError(self.message)
        else:
            if not match:
                raise ValidationError(self.message)


class MinValueValidator(Validator):
    """Validates minimum numeric value."""
    
    def __init__(self, min_value: int | float, message: str | None = None):
        self.min_value = min_value
        self.message = message or f"Must be at least {min_value}"
    
    def __call__(self, value: Any) -> None:
        if value is not None:
            try:
                if float(value) < self.min_value:
                    raise ValidationError(self.message)
            except (ValueError, TypeError):
                pass


class MaxValueValidator(Validator):
    """Validates maximum numeric value."""
    
    def __init__(self, max_value: int | float, message: str | None = None):
        self.max_value = max_value
        self.message = message or f"Must be at most {max_value}"
    
    def __call__(self, value: Any) -> None:
        if value is not None:
            try:
                if float(value) > self.max_value:
                    raise ValidationError(self.message)
            except (ValueError, TypeError):
                pass


class IntegerValidator(Validator):
    """Validates that value is an integer."""
    
    def __init__(self, message: str = "Enter a valid integer"):
        self.message = message
    
    def __call__(self, value: Any) -> None:
        if value is None or value == "":
            return
        try:
            int(value)
        except (ValueError, TypeError):
            raise ValidationError(self.message)


class DecimalValidator(Validator):
    """Validates that value is a decimal number."""
    
    def __init__(self, message: str = "Enter a valid number"):
        self.message = message
    
    def __call__(self, value: Any) -> None:
        if value is None or value == "":
            return
        try:
            float(value)
        except (ValueError, TypeError):
            raise ValidationError(self.message)


class ChoiceValidator(Validator):
    """Validates that value is in a list of choices."""
    
    def __init__(self, choices: list, message: str = "Select a valid choice"):
        self.choices = choices
        self.message = message
    
    def __call__(self, value: Any) -> None:
        if value is not None and str(value) not in [str(c) for c in self.choices]:
            raise ValidationError(self.message)


class FileExtensionValidator(Validator):
    """Validates file extension."""
    
    def __init__(
        self,
        allowed_extensions: list[str],
        message: str | None = None
    ):
        self.allowed_extensions = [e.lower() for e in allowed_extensions]
        self.message = message or f"File extension must be one of: {', '.join(allowed_extensions)}"
    
    def __call__(self, value: Any) -> None:
        if value is None:
            return
        
        if hasattr(value, 'name'):
            ext = value.name.rsplit('.', 1)[-1].lower()
            if ext not in self.allowed_extensions:
                raise ValidationError(self.message)


class FileSizeValidator(Validator):
    """Validates file size."""
    
    def __init__(self, max_size: int, message: str | None = None):
        self.max_size = max_size
        self.message = message or f"File size must be at most {max_size} bytes"
    
    def __call__(self, value: Any) -> None:
        if value is None:
            return
        
        if hasattr(value, 'size'):
            if value.size > self.max_size:
                raise ValidationError(self.message)


def validate_email(value: str) -> tuple[bool, str]:
    """
    Validate email address.
    
    Args:
        value: Email to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = EmailValidator()
    try:
        validator(value)
        return True, ""
    except ValidationError as e:
        return False, e.message


def validate_url(value: str) -> tuple[bool, str]:
    """
    Validate URL.
    
    Args:
        value: URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = URLValidator()
    try:
        validator(value)
        return True, ""
    except ValidationError as e:
        return False, e.message


def validate_required(value: Any) -> tuple[bool, str]:
    """
    Validate required field.
    
    Args:
        value: Value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = RequiredValidator()
    try:
        validator(value)
        return True, ""
    except ValidationError as e:
        return False, e.message


def validate_min_length(value: str, min_length: int) -> tuple[bool, str]:
    """
    Validate minimum length.
    
    Args:
        value: Value to validate
        min_length: Minimum required length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = MinLengthValidator(min_length)
    try:
        validator(value)
        return True, ""
    except ValidationError as e:
        return False, e.message


def validate_max_length(value: str, max_length: int) -> tuple[bool, str]:
    """
    Validate maximum length.
    
    Args:
        value: Value to validate
        max_length: Maximum allowed length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = MaxLengthValidator(max_length)
    try:
        validator(value)
        return True, ""
    except ValidationError as e:
        return False, e.message


def validate_regex(value: str, pattern: str, message: str = "Invalid format") -> tuple[bool, str]:
    """
    Validate against regex pattern.
    
    Args:
        value: Value to validate
        pattern: Regex pattern
        message: Error message
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = RegexValidator(pattern, message)
    try:
        validator(value)
        return True, ""
    except ValidationError as e:
        return False, e.message
