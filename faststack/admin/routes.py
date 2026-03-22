"""
FastStack Admin Routes

Provides routes for the admin panel including dashboard and CRUD operations.
"""

from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select, func, col, or_

from faststack.app import get_templates
from faststack.config import settings
from faststack.core.dependencies import AdminUser, CurrentUser, DBSession
from faststack.core.responses import is_htmx, HTMXResponse
from faststack.core.session import flash, get_flashes
from faststack.admin.registry import admin_registry, ModelAdmin
from faststack.auth.models import User

router = APIRouter(tags=["admin"])


def get_context(request: Request, **extra: Any) -> dict[str, Any]:
    """Get template context with common values."""
    context = {
        "request": request,
        "settings": settings,
        "menu_items": admin_registry.get_menu_items(),
        "flashes": get_flashes(request),
    }
    context.update(extra)
    return context


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, user: AdminUser):
    """Render admin dashboard."""
    templates = get_templates()

    # Get stats
    stats = {}
    for key, model_admin in admin_registry.get_all_models():
        # This would need a session, simplified for now
        stats[model_admin.name_plural] = 0

    context = get_context(
        request,
        title=f"{settings.ADMIN_SITE_TITLE} - Dashboard",
        user=user,
        stats=stats,
    )
    return templates.TemplateResponse("admin/dashboard.html", context)


@router.get("/{model_name}/", response_class=HTMLResponse)
async def model_list(
    request: Request,
    model_name: str,
    user: AdminUser,
    session: DBSession,
    page: int = Query(1, ge=1),
    search: str = Query(""),
):
    """Render model list view."""
    model_admin = admin_registry.get_model(model_name)
    if not model_admin:
        raise HTTPException(status_code=404, detail="Model not found")

    templates = get_templates()
    model = model_admin.model

    # Build query
    query = select(model)

    # Search
    if search and model_admin.search_fields:
        search_conditions = []
        for field in model_admin.search_fields:
            if hasattr(model, field):
                search_conditions.append(col(getattr(model, field)).contains(search))
        if search_conditions:
            query = query.where(or_(*search_conditions))

    # Ordering
    if model_admin.ordering:
        for order in model_admin.ordering:
            descending = order.startswith("-")
            field_name = order.lstrip("-")
            if hasattr(model, field_name):
                field = getattr(model, field_name)
                query = query.order_by(field.desc() if descending else field)
    elif hasattr(model, "id"):
        query = query.order_by(model.id.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = session.exec(count_query).one()

    # Pagination
    offset = (page - 1) * model_admin.list_per_page
    query = query.offset(offset).limit(model_admin.list_per_page)

    # Execute
    items = list(session.exec(query).all())

    # Calculate pagination info
    total_pages = (total + model_admin.list_per_page - 1) // model_admin.list_per_page

    context = get_context(
        request,
        title=f"{model_admin.name_plural} - {settings.ADMIN_SITE_TITLE}",
        user=user,
        model_admin=model_admin,
        items=items,
        page=page,
        total_pages=total_pages,
        total=total,
        search=search,
    )
    return templates.TemplateResponse("admin/list.html", context)


@router.get("/{model_name}/create/", response_class=HTMLResponse)
async def model_create_form(
    request: Request,
    model_name: str,
    user: AdminUser,
):
    """Render create form."""
    model_admin = admin_registry.get_model(model_name)
    if not model_admin:
        raise HTTPException(status_code=404, detail="Model not found")

    templates = get_templates()
    columns = model_admin.get_columns()

    context = get_context(
        request,
        title=f"Create {model_admin.name} - {settings.ADMIN_SITE_TITLE}",
        user=user,
        model_admin=model_admin,
        columns=columns,
        is_create=True,
    )
    return templates.TemplateResponse("admin/form.html", context)


@router.post("/{model_name}/create/")
async def model_create(
    request: Request,
    model_name: str,
    user: AdminUser,
    session: DBSession,
):
    """Handle create form submission."""
    model_admin = admin_registry.get_model(model_name)
    if not model_admin:
        raise HTTPException(status_code=404, detail="Model not found")

    model = model_admin.model

    # Get form data
    form_data = await request.form()

    # Build instance
    data = {}
    columns = model_admin.get_columns()

    for col in columns:
        if col.name in model_admin.exclude or not col.editable:
            continue

        value = form_data.get(col.name)
        if value is not None and value != "":
            # Type conversion
            if col.type == "number":
                try:
                    data[col.name] = int(value)
                except ValueError:
                    try:
                        data[col.name] = float(value)
                    except ValueError:
                        data[col.name] = value
            elif col.type == "checkbox":
                data[col.name] = value == "on" or value == "true"
            else:
                data[col.name] = value
        elif col.required and not col.primary_key:
            # Handle required fields
            pass

    # Create instance
    instance = model(**data)
    session.add(instance)
    session.commit()
    session.refresh(instance)

    if is_htmx(request):
        return HTMXResponse.redirect(f"/admin/{model_name}/{instance.id}/")

    flash(request, f"{model_admin.name} created successfully", "success")
    return RedirectResponse(
        url=f"/admin/{model_name}/{instance.id}/",
        status_code=302,
    )


@router.get("/{model_name}/{item_id}/", response_class=HTMLResponse)
async def model_detail(
    request: Request,
    model_name: str,
    item_id: int,
    user: AdminUser,
    session: DBSession,
):
    """Render detail/edit form."""
    model_admin = admin_registry.get_model(model_name)
    if not model_admin:
        raise HTTPException(status_code=404, detail="Model not found")

    model = model_admin.model
    instance = session.get(model, item_id)

    if not instance:
        raise HTTPException(status_code=404, detail="Item not found")

    templates = get_templates()
    columns = model_admin.get_columns()

    context = get_context(
        request,
        title=f"Edit {model_admin.name} #{item_id} - {settings.ADMIN_SITE_TITLE}",
        user=user,
        model_admin=model_admin,
        instance=instance,
        columns=columns,
        is_create=False,
    )
    return templates.TemplateResponse("admin/form.html", context)


@router.post("/{model_name}/{item_id}/")
async def model_update(
    request: Request,
    model_name: str,
    item_id: int,
    user: AdminUser,
    session: DBSession,
):
    """Handle update form submission."""
    model_admin = admin_registry.get_model(model_name)
    if not model_admin:
        raise HTTPException(status_code=404, detail="Model not found")

    model = model_admin.model
    instance = session.get(model, item_id)

    if not instance:
        raise HTTPException(status_code=404, detail="Item not found")

    # Get form data
    form_data = await request.form()

    # Update instance
    columns = model_admin.get_columns()

    for col in columns:
        if col.name in model_admin.exclude or col.name in model_admin.readonly_fields:
            continue

        value = form_data.get(col.name)
        if value is not None:
            # Type conversion
            if col.type == "number":
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
            elif col.type == "checkbox":
                value = value == "on" or value == "true"

            setattr(instance, col.name, value)

    # Update timestamp if available
    if hasattr(instance, "touch"):
        instance.touch()

    session.add(instance)
    session.commit()
    session.refresh(instance)

    if is_htmx(request):
        return HTMLResponse(
            content='<div class="alert alert-success">Saved successfully</div>'
        )

    flash(request, f"{model_admin.name} updated successfully", "success")
    return RedirectResponse(
        url=f"/admin/{model_name}/{item_id}/",
        status_code=302,
    )


@router.post("/{model_name}/{item_id}/delete/")
async def model_delete(
    request: Request,
    model_name: str,
    item_id: int,
    user: AdminUser,
    session: DBSession,
):
    """Handle delete action."""
    model_admin = admin_registry.get_model(model_name)
    if not model_admin:
        raise HTTPException(status_code=404, detail="Model not found")

    model = model_admin.model
    instance = session.get(model, item_id)

    if not instance:
        raise HTTPException(status_code=404, detail="Item not found")

    session.delete(instance)
    session.commit()

    if is_htmx(request):
        return HTMXResponse.redirect(f"/admin/{model_name}/")

    flash(request, f"{model_admin.name} deleted successfully", "success")
    return RedirectResponse(url=f"/admin/{model_name}/", status_code=302)


@router.delete("/{model_name}/{item_id}/")
async def model_delete_api(
    model_name: str,
    item_id: int,
    user: AdminUser,
    session: DBSession,
):
    """API endpoint for delete."""
    model_admin = admin_registry.get_model(model_name)
    if not model_admin:
        raise HTTPException(status_code=404, detail="Model not found")

    model = model_admin.model
    instance = session.get(model, item_id)

    if not instance:
        raise HTTPException(status_code=404, detail="Item not found")

    session.delete(instance)
    session.commit()

    return {"success": True}
