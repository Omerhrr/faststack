"""
Admin Views - CRUD views for admin interface.
"""

from typing import Any, Dict, List, Optional, Type
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, JSONResponse

from ...core.pagination import Paginator, EmptyPage, PageNotAnInteger
from ...core.messages import messages


class AdminView:
    """
    Base admin view.

    Provides common functionality for all admin views.
    """

    template_name: str = ''

    def __init__(self, model_admin: Any, admin_site: Any):
        self.model_admin = model_admin
        self.admin_site = admin_site
        self.model = model_admin.model

    def get_template_names(self) -> List[str]:
        """Get template names to try."""
        if self.template_name:
            return [self.template_name]
        return []

    def get_context_data(self, request: Request, **kwargs) -> dict:
        """Get context data for template."""
        context = {
            'request': request,
            'model_admin': self.model_admin,
            'opts': self.get_model_opts(),
            'site_header': self.admin_site.name.title(),
            'site_title': self.admin_site.name.title(),
            'title': '',
            **kwargs
        }
        return context

    def get_model_opts(self) -> dict:
        """Get model options for template."""
        return {
            'model_name': self.model.__name__.lower(),
            'model_name_plural': f"{self.model.__name__.lower()}s",
            'verbose_name': getattr(self.model, '__verbose_name__', self.model.__name__),
            'verbose_name_plural': getattr(self.model, '__verbose_name_plural__', f"{self.model.__name__}s"),
            'app_label': self.model.__module__.split('.')[0],
        }

    def render_to_response(self, context: dict, status: int = 200) -> HTMLResponse:
        """Render template to response."""
        template = self.get_template_names()[0] if self.get_template_names() else None

        if template:
            html = self._render_template(template, context)
        else:
            html = self._render_default(context)

        return HTMLResponse(html, status_code=status)

    def _render_template(self, template: str, context: dict) -> str:
        """Render a template with context."""
        # This would integrate with the template engine
        return f"<!-- Template: {template} -->"

    def _render_default(self, context: dict) -> str:
        """Default render method."""
        return f"<h1>Admin</h1>"


class AdminListView(AdminView):
    """
    List view for admin models.

    Displays a paginated, filterable, searchable list of model instances.
    """

    template_name = 'admin/change_list.html'

    async def get(self, request: Request) -> HTMLResponse:
        """Handle GET request for list view."""
        # Check permission
        if not self.model_admin.has_view_permission(request):
            return HTMLResponse('<h1>Permission Denied</h1>', status_code=403)

        # Get queryset
        queryset = await self.model_admin.aget_queryset(request)

        # Apply search
        search_term = request.query_params.get('q', '')
        if search_term:
            queryset, _ = self.model_admin.get_search_results(request, queryset, search_term)

        # Apply filters
        for filter_field in self.model_admin.list_filter:
            value = request.query_params.get(filter_field)
            if value:
                if hasattr(queryset, 'filter'):
                    queryset = queryset.filter(**{filter_field: value})

        # Apply ordering
        ordering = self.model_admin.get_ordering(request)
        if ordering and hasattr(queryset, 'order_by'):
            queryset = queryset.order_by(*ordering)

        # Paginate
        page_num = request.query_params.get('p', 1)
        per_page = self.model_admin.list_per_page

        try:
            paginator = Paginator(queryset, per_page)
            page = paginator.page(page_num)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)

        # Build context
        context = self.get_context_data(
            request,
            title=f'Select {self.get_model_opts()["verbose_name"]} to change',
            page=page,
            paginator=paginator,
            search_term=search_term,
            list_display=self.model_admin.get_list_display(request),
            list_filter=self.model_admin.get_list_filter(request),
            actions=self.model_admin.get_actions(request),
            has_add_permission=self.model_admin.has_add_permission(request),
            is_popup='popup' in request.query_params,
        )

        return self.render_to_response(context)

    async def post(self, request: Request) -> HTMLResponse:
        """Handle POST request for actions."""
        form = await request.form()

        action = form.get('action')
        selected = form.getlist('_selected_action')

        if action and selected:
            # Execute action
            actions = self.model_admin.get_actions(request)
            if action in actions:
                action_func = actions[action].func
                await action_func(request, selected)

        return RedirectResponse(url=request.url.path, status_code=302)


class AdminCreateView(AdminView):
    """
    Create view for admin models.

    Displays a form for creating new model instances.
    """

    template_name = 'admin/change_form.html'

    async def get(self, request: Request) -> HTMLResponse:
        """Handle GET request for create form."""
        if not self.model_admin.has_add_permission(request):
            return HTMLResponse('<h1>Permission Denied</h1>', status_code=403)

        context = self.get_context_data(
            request,
            title=f'Add {self.get_model_opts()["verbose_name"]}',
            form=self.get_form(),
            is_popup='popup' in request.query_params,
            show_save=True,
            show_save_as_new=self.model_admin.save_as,
            show_save_and_continue=True,
        )

        return self.render_to_response(context)

    async def post(self, request: Request) -> HTMLResponse:
        """Handle POST request to create object."""
        if not self.model_admin.has_add_permission(request):
            return HTMLResponse('<h1>Permission Denied</h1>', status_code=403)

        form = await request.form()

        # Create object
        obj = await self.create_object(form)

        # Success message
        messages.success(request, f'The {self.get_model_opts()["verbose_name"]} "{obj}" was added successfully.')

        # Redirect
        if '_save' in form:
            return RedirectResponse(url=f'../{self.get_model_opts()["model_name"]}/', status_code=302)
        elif '_addanother' in form:
            return RedirectResponse(url='./add/', status_code=302)
        else:
            return RedirectResponse(url=f'../{self.get_model_opts()["model_name"]}/{obj.id}/change/', status_code=302)

    def get_form(self) -> dict:
        """Get form configuration."""
        return {
            'fields': self.model_admin.fields,
            'fieldsets': self.model_admin.fieldsets,
            'readonly_fields': self.model_admin.readonly_fields,
        }

    async def create_object(self, form: dict) -> Any:
        """Create object from form data."""
        if hasattr(self.model, 'create'):
            return await self.model.create(**form)
        return None


class AdminUpdateView(AdminView):
    """
    Update view for admin models.

    Displays a form for editing existing model instances.
    """

    template_name = 'admin/change_form.html'

    async def get(self, request: Request, object_id: str) -> HTMLResponse:
        """Handle GET request for edit form."""
        obj = await self.get_object(object_id)

        if obj is None:
            return HTMLResponse('<h1>Not Found</h1>', status_code=404)

        if not self.model_admin.has_change_permission(request, obj):
            return HTMLResponse('<h1>Permission Denied</h1>', status_code=403)

        context = self.get_context_data(
            request,
            title=f'Change {self.get_model_opts()["verbose_name"]}',
            object=obj,
            form=self.get_form(obj),
            is_popup='popup' in request.query_params,
            show_save=True,
            show_save_as_new=self.model_admin.save_as,
            show_save_and_continue=True,
            show_delete=self.model_admin.has_delete_permission(request, obj),
        )

        return self.render_to_response(context)

    async def post(self, request: Request, object_id: str) -> HTMLResponse:
        """Handle POST request to update object."""
        obj = await self.get_object(object_id)

        if obj is None:
            return HTMLResponse('<h1>Not Found</h1>', status_code=404)

        if not self.model_admin.has_change_permission(request, obj):
            return HTMLResponse('<h1>Permission Denied</h1>', status_code=403)

        form = await request.form()

        # Update object
        await self.update_object(obj, form)

        # Success message
        messages.success(request, f'The {self.get_model_opts()["verbose_name"]} "{obj}" was changed successfully.')

        # Redirect
        if '_save' in form:
            return RedirectResponse(url='../../', status_code=302)
        elif '_continue' in form:
            return RedirectResponse(url='./', status_code=302)
        elif '_addanother' in form:
            return RedirectResponse(url='../add/', status_code=302)
        else:
            return RedirectResponse(url='../../', status_code=302)

    async def get_object(self, object_id: str) -> Any:
        """Get object by ID."""
        if hasattr(self.model, 'get'):
            return await self.model.get(id=object_id)
        return None

    def get_form(self, obj: Any) -> dict:
        """Get form configuration."""
        return {
            'fields': self.model_admin.fields,
            'fieldsets': self.model_admin.fieldsets,
            'readonly_fields': self.model_admin.readonly_fields,
            'instance': obj,
        }

    async def update_object(self, obj: Any, form: dict) -> None:
        """Update object from form data."""
        for key, value in form.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        if hasattr(obj, 'save'):
            await obj.save()


class AdminDeleteView(AdminView):
    """
    Delete view for admin models.

    Displays a confirmation page for deleting model instances.
    """

    template_name = 'admin/delete_confirmation.html'

    async def get(self, request: Request, object_id: str) -> HTMLResponse:
        """Handle GET request for delete confirmation."""
        obj = await self.get_object(object_id)

        if obj is None:
            return HTMLResponse('<h1>Not Found</h1>', status_code=404)

        if not self.model_admin.has_delete_permission(request, obj):
            return HTMLResponse('<h1>Permission Denied</h1>', status_code=403)

        context = self.get_context_data(
            request,
            title=f'Delete {self.get_model_opts()["verbose_name"]}',
            object=obj,
            deleted_objects=await self.get_deleted_objects(obj),
        )

        return self.render_to_response(context)

    async def post(self, request: Request, object_id: str) -> HTMLResponse:
        """Handle POST request to delete object."""
        obj = await self.get_object(object_id)

        if obj is None:
            return HTMLResponse('<h1>Not Found</h1>', status_code=404)

        if not self.model_admin.has_delete_permission(request, obj):
            return HTMLResponse('<h1>Permission Denied</h1>', status_code=403)

        display_name = str(obj)
        await self.delete_object(obj)

        # Success message
        messages.success(request, f'The {self.get_model_opts()["verbose_name"]} "{display_name}" was deleted successfully.')

        return RedirectResponse(url='../../', status_code=302)

    async def get_object(self, object_id: str) -> Any:
        """Get object by ID."""
        if hasattr(self.model, 'get'):
            return await self.model.get(id=object_id)
        return None

    async def get_deleted_objects(self, obj: Any) -> List[str]:
        """Get list of objects that will be deleted."""
        # This would check related objects and cascade deletes
        return [str(obj)]

    async def delete_object(self, obj: Any) -> None:
        """Delete the object."""
        if hasattr(obj, 'delete'):
            await obj.delete()


class AdminDetailView(AdminView):
    """
    Detail view for admin models.

    Displays a read-only view of a model instance.
    """

    template_name = 'admin/change_form.html'

    async def get(self, request: Request, object_id: str) -> HTMLResponse:
        """Handle GET request for detail view."""
        obj = await self.get_object(object_id)

        if obj is None:
            return HTMLResponse('<h1>Not Found</h1>', status_code=404)

        if not self.model_admin.has_view_permission(request, obj):
            return HTMLResponse('<h1>Permission Denied</h1>', status_code=403)

        context = self.get_context_data(
            request,
            title=f'View {self.get_model_opts()["verbose_name"]}',
            object=obj,
            form=self.get_form(obj),
            is_popup='popup' in request.query_params,
            show_save=False,
            readonly=True,
        )

        return self.render_to_response(context)

    async def get_object(self, object_id: str) -> Any:
        """Get object by ID."""
        if hasattr(self.model, 'get'):
            return await self.model.get(id=object_id)
        return None

    def get_form(self, obj: Any) -> dict:
        """Get form configuration (all fields readonly)."""
        return {
            'fields': self.model_admin.fields,
            'fieldsets': self.model_admin.fieldsets,
            'readonly_fields': self.model_admin.fields,  # All readonly
            'instance': obj,
        }
