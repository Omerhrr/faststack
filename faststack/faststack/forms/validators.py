"""Form Validators"""
import re


class ValidationError(Exception):
    pass


class Validator:
    def __call__(self, value):
        pass


class RequiredValidator(Validator):
    def __call__(self, value):
        if not value:
            raise ValidationError("This field is required")


class EmailValidator(Validator):
    pattern = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
    
    def __call__(self, value):
        if value and not self.pattern.match(value):
            raise ValidationError("Enter a valid email")


class MinLengthValidator(Validator):
    def __init__(self, min_length):
        self.min_length = min_length
    
    def __call__(self, value):
        if value and len(value) < self.min_length:
            raise ValidationError(f"Minimum {self.min_length} characters")
