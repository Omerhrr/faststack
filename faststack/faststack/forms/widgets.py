"""
Form Widgets

Provides widget classes for rendering form fields as HTML.
"""

from typing import Any
import json


class Widget:
    """
    Base widget class for form field rendering.
    """
    
    def __init__(self, attrs: dict | None = None):
        """
        Initialize widget.
        
        Args:
            attrs: HTML attributes to add to the widget
        """
        self.attrs = attrs or {}
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        """
        Render the widget as HTML.
        
        Args:
            name: Field name
            value: Current field value
            attrs: Additional HTML attributes
            
        Returns:
            HTML string
        """
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        return f'<input name="{name}" value="{value or ""}" {attr_str}>'
    
    def _build_attrs(self, attrs: dict) -> str:
        """Build HTML attribute string from dict."""
        parts = []
        for key, value in attrs.items():
            if value is True:
                parts.append(f'{key}')
            elif value is not False and value is not None:
                parts.append(f'{key}="{value}"')
        return ' '.join(parts)


class TextInput(Widget):
    """Text input widget."""
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {}), 'type': 'text'}
        attr_str = self._build_attrs(final_attrs)
        return f'<input type="text" name="{name}" value="{value or ""}" {attr_str}>'


class PasswordInput(Widget):
    """Password input widget."""
    
    def __init__(self, attrs: dict | None = None, render_value: bool = False):
        super().__init__(attrs)
        self.render_value = render_value
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        value_str = f'value="{value}"' if self.render_value and value else ''
        return f'<input type="password" name="{name}" {value_str} {attr_str}>'


class EmailInput(Widget):
    """Email input widget."""
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        return f'<input type="email" name="{name}" value="{value or ""}" {attr_str}>'


class NumberInput(Widget):
    """Number input widget."""
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        return f'<input type="number" name="{name}" value="{value or ""}" {attr_str}>'


class Textarea(Widget):
    """Textarea widget."""
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        return f'<textarea name="{name}" {attr_str}>{value or ""}</textarea>'


class Select(Widget):
    """Select dropdown widget."""
    
    def __init__(self, choices: list | None = None, attrs: dict | None = None):
        super().__init__(attrs)
        self.choices = choices or []
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        
        options = []
        for choice in self.choices:
            if isinstance(choice, (list, tuple)) and len(choice) >= 2:
                choice_value, choice_label = choice[0], choice[1]
            else:
                choice_value = choice_label = str(choice)
            
            selected = 'selected' if str(value) == str(choice_value) else ''
            options.append(f'<option value="{choice_value}" {selected}>{choice_label}</option>')
        
        return f'<select name="{name}" {attr_str}>{"".join(options)}</select>'


class CheckboxInput(Widget):
    """Checkbox input widget."""
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        checked = 'checked' if value else ''
        return f'<input type="checkbox" name="{name}" {checked} {attr_str}>'


class RadioSelect(Widget):
    """Radio button select widget."""
    
    def __init__(self, choices: list | None = None, attrs: dict | None = None):
        super().__init__(attrs)
        self.choices = choices or []
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        
        radios = []
        for choice in self.choices:
            if isinstance(choice, (list, tuple)) and len(choice) >= 2:
                choice_value, choice_label = choice[0], choice[1]
            else:
                choice_value = choice_label = str(choice)
            
            checked = 'checked' if str(value) == str(choice_value) else ''
            radios.append(
                f'<label><input type="radio" name="{name}" value="{choice_value}" {checked} {attr_str}> {choice_label}</label>'
            )
        
        return '<br>'.join(radios)


class FileInput(Widget):
    """File input widget."""
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        return f'<input type="file" name="{name}" {attr_str}>'


class HiddenInput(Widget):
    """Hidden input widget."""
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        return f'<input type="hidden" name="{name}" value="{value or ""}" {attr_str}>'


class DateInput(Widget):
    """Date input widget."""
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        
        if hasattr(value, 'isoformat'):
            value = value.isoformat()
        
        return f'<input type="date" name="{name}" value="{value or ""}" {attr_str}>'


class DateTimeInput(Widget):
    """DateTime input widget."""
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        
        if hasattr(value, 'isoformat'):
            value = value.isoformat()
        
        return f'<input type="datetime-local" name="{name}" value="{value or ""}" {attr_str}>'


class URLInput(Widget):
    """URL input widget."""
    
    def render(self, name: str, value: Any, attrs: dict | None = None) -> str:
        final_attrs = {**self.attrs, **(attrs or {})}
        attr_str = self._build_attrs(final_attrs)
        return f'<input type="url" name="{name}" value="{value or ""}" {attr_str}>'
