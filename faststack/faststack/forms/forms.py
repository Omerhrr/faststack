"""Form Classes"""
from typing import Any


class FormMetaclass(type):
    def __new__(mcs, name, bases, namespace):
        fields = {}
        for base in bases:
            if hasattr(base, '_fields'):
                fields.update(base._fields)
        for key, value in namespace.items():
            if hasattr(value, 'clean'):
                value.name = key
                fields[key] = value
        cls = super().__new__(mcs, name, bases, namespace)
        cls._fields = fields
        return cls


class Form(metaclass=FormMetaclass):
    """Base form class."""
    
    def __init__(self, data=None, files=None, initial=None):
        self.data = data or {}
        self.files = files or {}
        self.initial = initial or {}
        self._errors = {}
        self._cleaned_data = {}
    
    def is_valid(self) -> bool:
        self._errors = {}
        self._cleaned_data = {}
        valid = True
        for name, field in self._fields.items():
            try:
                value = self.data.get(name)
                self._cleaned_data[name] = value
            except Exception as e:
                self._errors[name] = [str(e)]
                valid = False
        return valid
    
    @property
    def errors(self):
        return self._errors
    
    @property
    def cleaned_data(self):
        return self._cleaned_data
    
    def as_p(self) -> str:
        parts = []
        for name, field in self._fields.items():
            parts.append(f'<p><label for="{name}">{name}</label></p>')
        return '\n'.join(parts)


class ModelForm(Form):
    """Form tied to a model."""
    
    class Meta:
        model = None
        fields = None
        exclude = None
