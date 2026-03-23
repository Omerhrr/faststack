"""
Admin Registry - ModelAdmin registration and site management.
"""

from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from dataclasses import dataclass, field
import inspect

T = TypeVar('T')


@dataclass
class AdminAction:
    """
    Admin action that can be performed on selected items.

    Example:
        def make_published(modeladmin, request, queryset):
            queryset.update(status='published')
        make_published.short_description = "Mark selected as published"
    """

    func: Callable
    name: str
    short_description: str = ''

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


@dataclass
class AdminField:
    """Admin field configuration."""

    name: str
    label: str = ''
    widget: Any = None
    readonly: bool = False
    help_text: str = ''
    required: bool = True

    def __post_init__(self):
        if not self.label:
            self.label = self.name.replace('_', ' ').title()


@dataclass
class AdminListFilter:
    """Admin list filter configuration."""

    field: str
    title: str = ''
    lookup_choices: List[Any] = field(default_factory=list)

    def __post_init__(self):
        if not self.title:
            self.title = self.field.replace('_', ' ').title()


class ModelAdmin:
    """
    Configuration for a model's admin interface.

    Attributes:
        model: The model class
        list_display: Fields to display in list view
        list_display_links: Fields that link to edit page
        list_filter: Fields to filter by in sidebar
        list_select_related: Related fields to select (optimization)
        list_per_page: Items per page in list view
        list_max_show_all: Max items for "show all"
        list_editable: Fields editable in list view
        search_fields: Fields to search in
        date_hierarchy: Date field for hierarchical navigation
        save_as: Show "Save as new" button
        save_as_continue: Redirect to edit after "Save as new"
        save_on_top: Show save buttons at top of form
        ordering: Default ordering
        readonly_fields: Fields that cannot be edited
        exclude: Fields to exclude from forms
        fields: Fields to show in order
        fieldsets: Grouped fields configuration
        raw_id_fields: Fields using raw ID input
        prepopulated_fields: Fields auto-populated from other fields
        filter_horizontal: Many-to-many with horizontal filter
        filter_vertical: Many-to-many with vertical filter
        inlines: Inline model admins
        actions: Custom actions for selected items
        actions_on_top: Show actions at top
        actions_on_bottom: Show actions at bottom
        actions_selection_counter: Show selection counter

    Example:
        class UserAdmin(ModelAdmin):
            list_display = ['username', 'email', 'is_active', 'date_joined']
            list_filter = ['is_active', 'is_staff']
            search_fields = ['username', 'email']
            ordering = ['-date_joined']
            readonly_fields = ['date_joined', 'last_login']
    """

    model: Type = None

    # List view options
    list_display: List[str] = ['__str__']
    list_display_links: List[str] = []
    list_filter: List[Union[str, Type]] = []
    list_select_related: List[str] = []
    list_per_page: int = 100
    list_max_show_all: int = 200
    list_editable: List[str] = []

    # Search options
    search_fields: List[str] = []
    search_help_text: str = ''

    # Date hierarchy
    date_hierarchy: str = ''

    # Save options
    save_as: bool = False
    save_as_continue: bool = True
    save_on_top: bool = False

    # Ordering
    ordering: List[str] = []

    # Form options
    readonly_fields: List[str] = []
    exclude: List[str] = []
    fields: List[str] = []
    fieldsets: List[tuple] = []

    # Related fields
    raw_id_fields: List[str] = []
    prepopulated_fields: Dict[str, List[str]] = {}
    filter_horizontal: List[str] = []
    filter_vertical: List[str] = []

    # Inlines
    inlines: List[Type] = []

    # Actions
    actions: List[Callable] = []
    actions_on_top: bool = True
    actions_on_bottom: bool = False
    actions_selection_counter: bool = True

    # Permissions
    def has_view_permission(self, request: Any, obj: Any = None) -> bool:
        """Check if user can view this model."""
        user = getattr(request, 'user', None)
        if user is None:
            return True
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return True
        return user.has_perm(f'{self.model.__module__}.view_{self.model.__name__.lower()}')

    def has_add_permission(self, request: Any) -> bool:
        """Check if user can add new objects."""
        user = getattr(request, 'user', None)
        if user is None:
            return True
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return True
        return user.has_perm(f'{self.model.__module__}.add_{self.model.__name__.lower()}')

    def has_change_permission(self, request: Any, obj: Any = None) -> bool:
        """Check if user can change objects."""
        user = getattr(request, 'user', None)
        if user is None:
            return True
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return True
        return user.has_perm(f'{self.model.__module__}.change_{self.model.__name__.lower()}')

    def has_delete_permission(self, request: Any, obj: Any = None) -> bool:
        """Check if user can delete objects."""
        user = getattr(request, 'user', None)
        if user is None:
            return True
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return True
        return user.has_perm(f'{self.model.__module__}.delete_{self.model.__name__.lower()}')

    # Queryset customization
    def get_queryset(self, request: Any) -> Any:
        """Get the queryset for list view."""
        return self.model.all() if hasattr(self.model, 'all') else []

    async def aget_queryset(self, request: Any) -> Any:
        """Async get the queryset for list view."""
        if hasattr(self.model, 'all'):
            return await self.model.all()
        return []

    def get_search_results(self, request: Any, queryset: Any, search_term: str) -> tuple:
        """
        Filter queryset by search term.

        Returns:
            Tuple of (filtered_queryset, may_have_duplicates)
        """
        if not search_term or not self.search_fields:
            return queryset, False

        from ...orm.query import Q

        q = Q()
        for field in self.search_fields:
            q |= Q(**{f'{field}__icontains': search_term})

        # Apply filter
        if hasattr(queryset, 'filter'):
            queryset = queryset.filter(q)

        return queryset, False

    # URL generation
    def get_urls(self) -> List[tuple]:
        """Get URL patterns for this admin."""
        return []

    @property
    def urls(self) -> List[tuple]:
        """URL patterns for this admin."""
        return self.get_urls()

    # Helper methods
    def get_list_display(self, request: Any) -> List[str]:
        """Get list display fields for request."""
        return self.list_display

    def get_list_filter(self, request: Any) -> List:
        """Get list filters for request."""
        return self.list_filter

    def get_readonly_fields(self, request: Any, obj: Any = None) -> List[str]:
        """Get readonly fields for request."""
        return self.readonly_fields

    def get_fields(self, request: Any, obj: Any = None) -> List[str]:
        """Get form fields for request."""
        if self.fields:
            return self.fields

        # Auto-detect from model
        if hasattr(self.model, '__table__'):
            return [c.name for c in self.model.__table__.columns]

        return []

    def get_fieldsets(self, request: Any, obj: Any = None) -> List[tuple]:
        """Get fieldsets for request."""
        if self.fieldsets:
            return self.fieldsets

        fields = self.get_fields(request, obj)
        if fields:
            return [(None, {'fields': fields})]

        return []

    def get_ordering(self, request: Any) -> List[str]:
        """Get ordering for request."""
        return self.ordering

    def get_actions(self, request: Any) -> Dict[str, AdminAction]:
        """Get available actions for request."""
        actions = {}

        for action in self.actions:
            if isinstance(action, str):
                # Action by name
                func = getattr(self, action, None)
                if func:
                    actions[action] = AdminAction(
                        func=func,
                        name=action,
                        short_description=getattr(func, 'short_description', action)
                    )
            elif callable(action):
                # Action function
                name = action.__name__
                actions[name] = AdminAction(
                    func=action,
                    name=name,
                    short_description=getattr(action, 'short_description', name)
                )

        return actions


class InlineModelAdmin(ModelAdmin):
    """
    Inline admin for editing related objects.

    Example:
        class CommentInline(InlineModelAdmin):
            model = Comment
            extra = 1
    """

    model: Type = None
    fk_name: str = ''
    extra: int = 3
    max_num: int = None
    min_num: int = 0
    can_delete: bool = True
    show_change_link: bool = False
    verbose_name: str = ''
    verbose_name_plural: str = ''
    template: str = 'admin/edit_inline/tabular.html'


class TabularInline(InlineModelAdmin):
    """Tabular inline admin (table format)."""
    template = 'admin/edit_inline/tabular.html'


class StackedInline(InlineModelAdmin):
    """Stacked inline admin (stacked format)."""
    template = 'admin/edit_inline/stacked.html'


class AdminSite:
    """
    Admin site that manages all registered models.

    Example:
        admin_site = AdminSite(name='admin')
        admin_site.register(User, UserAdmin)
    """

    def __init__(self, name: str = 'admin'):
        self.name = name
        self._registry: Dict[Type, ModelAdmin] = {}

    def __repr__(self) -> str:
        return f"<AdminSite: {self.name}, {len(self._registry)} models>"

    @property
    def registry(self) -> Dict[Type, ModelAdmin]:
        """Get the model registry."""
        return self._registry

    def is_registered(self, model: Type) -> bool:
        """Check if a model is registered."""
        return model in self._registry

    def register(
        self,
        model_or_iterable: Union[Type, List[Type]],
        admin_class: Type[ModelAdmin] = None,
        **options
    ) -> Callable:
        """
        Register model(s) with the admin.

        Can be used as a decorator or function.

        Args:
            model_or_iterable: Model class or list of models
            admin_class: ModelAdmin class (optional if using as decorator)
            **options: Options to pass to ModelAdmin

        Returns:
            Decorator function if used as decorator

        Example:
            # As function
            admin.register(User, UserAdmin)

            # As decorator
            @admin.register(User)
            class UserAdmin(ModelAdmin):
                pass

            # With options
            admin.register(User, list_display=['username', 'email'])
        """
        if admin_class is None:
            # Used as decorator
            def decorator(admin_cls):
                self.register(model_or_iterable, admin_cls, **options)
                return admin_cls
            return decorator

        # Handle single model or list
        models = [model_or_iterable] if not isinstance(model_or_iterable, (list, tuple)) else model_or_iterable

        for model in models:
            if model in self._registry:
                raise ValueError(f"Model {model.__name__} is already registered")

            # Create admin instance
            admin_instance = admin_class(model, **options) if options else admin_class(model)
            admin_instance.model = model

            self._registry[model] = admin_instance

        return None

    def unregister(self, model: Type) -> None:
        """Unregister a model from the admin."""
        if model in self._registry:
            del self._registry[model]

    def get_model_admin(self, model: Type) -> Optional[ModelAdmin]:
        """Get ModelAdmin for a model."""
        return self._registry.get(model)

    def get_urls(self) -> List[tuple]:
        """Get all URL patterns for this admin site."""
        urls = []

        # Index
        urls.append(('/', self.index, {'name': 'index'}))

        # Login/logout
        urls.append(('/login/', self.login, {'name': 'login'}))
        urls.append(('/logout/', self.logout, {'name': 'logout'}))

        # Model URLs
        for model, model_admin in self._registry.items():
            model_name = model.__name__.lower()
            urls.append((f'/{model.__module__}/{model_name}/', model_admin.urls))

        return urls

    async def index(self, request: Any) -> Any:
        """Admin index page."""
        from starlette.responses import HTMLResponse

        # Build context
        context = {
            'title': 'Site Administration',
            'site_header': self.name.title(),
            'site_title': self.name.title(),
            'models': [
                {
                    'name': model.__name__,
                    'module': model.__module__,
                    'admin': admin,
                    'url': f'/{model.__module__}/{model.__name__.lower()}/',
                }
                for model, admin in self._registry.items()
            ]
        }

        # Render template
        html = self._render_index(context)
        return HTMLResponse(html)

    async def login(self, request: Any) -> Any:
        """Admin login page."""
        from starlette.responses import HTMLResponse
        html = '<h1>Admin Login</h1><form>...</form>'
        return HTMLResponse(html)

    async def logout(self, request: Any) -> Any:
        """Admin logout."""
        from starlette.responses import RedirectResponse
        return RedirectResponse(url='/admin/', status_code=302)

    def _render_index(self, context: dict) -> str:
        """Render admin index page."""
        models_html = ''
        for model_info in context['models']:
            models_html += f'''
                <tr>
                    <td>{model_info['name']}</td>
                    <td>{model_info['module']}</td>
                    <td><a href="{model_info['url']}">Manage</a></td>
                </tr>
            '''

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{context['title']}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; }}
                .header {{ background: #417690; color: white; padding: 20px; margin: -20px -20px 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background: #f5f5f5; }}
                a {{ color: #447e9b; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{context['site_header']}</h1>
            </div>
            <h2>Models</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Module</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {models_html}
                </tbody>
            </table>
        </body>
        </html>
        '''


# Default admin site instance
admin = AdminSite()


def register(model: Type, admin_class: Type[ModelAdmin] = None, **options) -> Callable:
    """
    Convenience function to register with default admin site.

    Example:
        @register(User)
        class UserAdmin(ModelAdmin):
            pass
    """
    return admin.register(model, admin_class, **options)
