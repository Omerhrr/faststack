"""Form Fields"""
from typing import Any


class Field:
    """Base field class."""
    
    def __init__(self, required=True, label=None, help_text="", initial=None):
        self.required = required
        self.label = label
        self.help_text = help_text
        self.initial = initial
        self.name = None
    
    def clean(self, value):
        if self.required and not value:
            raise ValueError("This field is required")
        return value


class CharField(Field):
    def __init__(self, max_length=None, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length


class EmailField(CharField):
    pass


class IntegerField(Field):
    pass


class BooleanField(Field):
    pass


class ChoiceField(Field):
    def __init__(self, choices=None, **kwargs):
        super().__init__(**kwargs)
        self.choices = choices or []
