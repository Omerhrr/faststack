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
        """Validate all fields and return True if all are valid."""
        self._errors = {}
        self._cleaned_data = {}
        valid = True
        
        for name, field in self._fields.items():
            raw_value = self.data.get(name)
            
            # Run field validation
            is_valid, error_msg = field.validate(raw_value)
            if not is_valid:
                self._errors[name] = [error_msg]
                valid = False
                continue
            
            # Run field clean method
            try:
                cleaned_value = field.clean(raw_value)
                self._cleaned_data[name] = cleaned_value
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
    
    @property
    def fields(self):
        return self._fields
    
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
    
    def __init__(self, data=None, files=None, initial=None, instance=None):
        self.instance = instance
        super().__init__(data, files, initial)
        
        # Auto-generate fields from model if not already defined
        if not self._fields and self.Meta.model:
            self._generate_fields_from_model()
    
    def _generate_fields_from_model(self):
        """Generate form fields from model."""
        from faststack.faststack.forms.fields import CharField, IntegerField, BooleanField
        
        model = getattr(self.Meta, 'model', None)
        fields_to_include = getattr(self.Meta, 'fields', None) or []
        exclude = getattr(self.Meta, 'exclude', None) or []
        
        if not model:
            return
        
        if hasattr(model, '__annotations__'):
            for field_name, field_type in model.__annotations__.items():
                # Skip if fields list is specified and this field isn't in it
                if fields_to_include and field_name not in fields_to_include:
                    continue
                
                # Skip excluded fields
                if field_name in exclude:
                    continue
                
                # Skip internal fields
                if field_name.startswith('_'):
                    continue
                
                # Create appropriate field based on type
                if field_type == str or (hasattr(field_type, '__origin__') and field_type.__origin__ is str):
                    self._fields[field_name] = CharField(required=False)
                elif field_type == int:
                    self._fields[field_name] = IntegerField(required=False)
                elif field_type == bool:
                    self._fields[field_name] = BooleanField(required=False)
                else:
                    # Default to CharField
                    self._fields[field_name] = CharField(required=False)
        
        # Set field names
        for name, field in self._fields.items():
            field.name = name
