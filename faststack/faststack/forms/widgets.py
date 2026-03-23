"""Form Widgets"""


class Widget:
    def __init__(self, attrs=None):
        self.attrs = attrs or {}
    
    def render(self, name, value, attrs=None):
        return f'<input name="{name}" value="{value or ""}">'


class TextInput(Widget):
    pass


class PasswordInput(Widget):
    def render(self, name, value, attrs=None):
        return f'<input type="password" name="{name}">'


class EmailInput(Widget):
    def render(self, name, value, attrs=None):
        return f'<input type="email" name="{name}" value="{value or ""}">'


class Textarea(Widget):
    def render(self, name, value, attrs=None):
        return f'<textarea name="{name}">{value or ""}</textarea>'


class Select(Widget):
    def __init__(self, choices=None, **kwargs):
        super().__init__(**kwargs)
        self.choices = choices or []
    
    def render(self, name, value, attrs=None):
        options = ''.join(f'<option value="{v}">{l}</option>' for v, l in self.choices)
        return f'<select name="{name}">{options}</select>'
