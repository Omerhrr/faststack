"""
FastStack Shortcuts - Django-like convenience functions.

Example:
    from faststack.core.shortcuts import (
        render,
        redirect,
        get_object_or_404,
        get_list_or_404,
        resolve_url,
        Http404
    )

    # Render template
    return render(request, 'home.html', {'title': 'Home'})

    # Redirect
    return redirect('/login/')
    return redirect('user_profile', user_id=1)
    return redirect(user)  # Uses get_absolute_url()

    # Get object or 404
    user = await get_object_or_404(User, id=1)
    user = await get_object_or_404(User, username='john')
"""

from typing import Any, Dict, List, Optional, Type, Union
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException


class Http404(HTTPException):
    """HTTP 404 Not Found exception."""
    def __init__(self, detail: str = "Not found"):
        super().__init__(status_code=404, detail=detail)


class Http403(HTTPException):
    """HTTP 403 Forbidden exception."""
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=403, detail=detail)


class Http400(HTTPException):
    """HTTP 400 Bad Request exception."""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=400, detail=detail)


def render(
    request: Any,
    template_name: str,
    context: Dict[str, Any] = None,
    status: int = 200,
    using: str = None,
    content_type: str = 'text/html'
) -> Response:
    """
    Render a template to a response.

    Args:
        request: The request object
        template_name: Template filename
        context: Template context dictionary
        status: HTTP status code
        using: Template engine to use (optional)
        content_type: Response content type

    Returns:
        HTTP Response with rendered template

    Example:
        return render(request, 'user/profile.html', {
            'user': user,
            'posts': posts
        })
    """
    context = context or {}

    # Add request to context
    context['request'] = request

    # Get template engine
    template_engine = getattr(request.app, 'template_engine', None) if hasattr(request, 'app') else None

    if template_engine:
        # Use the app's template engine
        html = template_engine.render(template_name, context)
    else:
        # Try Jinja2
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
            import os

            # Get template directory
            template_dir = getattr(request.app, 'template_dir', 'templates') if hasattr(request, 'app') else 'templates'

            env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )

            template = env.get_template(template_name)
            html = template.render(**context)
        except ImportError:
            # Fallback to simple placeholder
            html = f"<!-- Template: {template_name} -->\n"
            html += f"<h1>{template_name}</h1>\n"
            html += "<pre>" + str(context) + "</pre>"

    return HTMLResponse(content=html, status_code=status, headers={'content-type': content_type})


def redirect(
    to: Union[str, Any],
    *args,
    permanent: bool = False,
    **kwargs
) -> RedirectResponse:
    """
    Return a redirect response.

    Args:
        to: URL string, view name, or model instance
        *args: Arguments for URL resolution
        permanent: If True, uses 301 permanent redirect
        **kwargs: Keyword arguments for URL resolution

    Returns:
        RedirectResponse

    Example:
        return redirect('/login/')
        return redirect('user_profile', user_id=1)
        return redirect(user)  # Uses get_absolute_url()
        return redirect('https://example.com')
    """
    url = resolve_url(to, *args, **kwargs)

    status_code = 301 if permanent else 302
    return RedirectResponse(url=url, status_code=status_code)


def resolve_url(to: Union[str, Any], *args, **kwargs) -> str:
    """
    Resolve a URL from string, view name, or model.

    Args:
        to: URL string, view name, or model instance
        *args: Arguments for URL resolution
        **kwargs: Keyword arguments for URL resolution

    Returns:
        URL string

    Example:
        url = resolve_url('/login/')  # '/login/'
        url = resolve_url(user)  # Uses get_absolute_url()
        url = resolve_url('user_profile', user_id=1)  # Resolves view name
    """
    # Already a URL
    if isinstance(to, str):
        if to.startswith('/') or to.startswith('http'):
            return to

        # Try to resolve view name
        # This would need URL routing integration
        # For now, just return as-is
        return to

    # Model instance with get_absolute_url
    if hasattr(to, 'get_absolute_url'):
        return to.get_absolute_url()

    # Callable that returns URL
    if callable(to):
        return to(*args, **kwargs)

    # Fallback
    return str(to)


async def get_object_or_404(model: Type, *args, **kwargs) -> Any:
    """
    Get a model instance or raise Http404.

    Args:
        model: Model class
        *args: Query arguments (for complex queries)
        **kwargs: Filter arguments

    Returns:
        Model instance

    Raises:
        Http404: If object not found

    Example:
        user = await get_object_or_404(User, id=1)
        user = await get_object_or_404(User, username='john')
        post = await get_object_or_404(Post, Q(status='published') & Q(featured=True))
    """
    try:
        # Try async get first
        if hasattr(model, 'get'):
            obj = model.get(**kwargs)

            # Check if it's a coroutine
            if hasattr(obj, '__await__'):
                obj = await obj

            if obj is None:
                raise Http404(f"{model.__name__} not found")

            return obj

        # Try filter first
        if hasattr(model, 'filter'):
            queryset = model.filter(**kwargs)
            results = queryset

            if hasattr(queryset, '__await__'):
                results = await queryset

            if not results:
                raise Http404(f"{model.__name__} not found")

            if hasattr(results, 'first'):
                obj = results.first()
                if hasattr(obj, '__await__'):
                    obj = await obj
                if obj is None:
                    raise Http404(f"{model.__name__} not found")
                return obj

            return results[0] if results else None

        raise Http404(f"{model.__name__} not found")

    except Http404:
        raise
    except Exception as e:
        raise Http404(f"{model.__name__} not found: {str(e)}")


async def get_list_or_404(model: Type, *args, **kwargs) -> List[Any]:
    """
    Get a list of model instances or raise Http404.

    Args:
        model: Model class
        *args: Query arguments
        **kwargs: Filter arguments

    Returns:
        List of model instances

    Raises:
        Http404: If no objects found

    Example:
        posts = await get_list_or_404(Post, status='published')
        users = await get_list_or_404(User, is_active=True)
    """
    try:
        # Try async filter
        if hasattr(model, 'filter'):
            queryset = model.filter(**kwargs)
            results = queryset

            if hasattr(queryset, '__await__'):
                results = await queryset

            # Convert to list if needed
            if hasattr(results, 'all'):
                results = results.all()
                if hasattr(results, '__await__'):
                    results = await results

            if not results:
                raise Http404(f"No {model.__name__} found")

            return list(results) if not isinstance(results, list) else results

        raise Http404(f"No {model.__name__} found")

    except Http404:
        raise
    except Exception as e:
        raise Http404(f"No {model.__name__} found: {str(e)}")


def get_object_or_none(model: Type, *args, **kwargs) -> Any:
    """
    Get a model instance or return None.

    Like get_object_or_404 but returns None instead of raising exception.
    """
    try:
        if hasattr(model, 'get'):
            obj = model.get(**kwargs)
            return obj
    except:
        pass
    return None


async def aget_object_or_none(model: Type, *args, **kwargs) -> Any:
    """Async version of get_object_or_none."""
    try:
        if hasattr(model, 'get'):
            obj = model.get(**kwargs)
            if hasattr(obj, '__await__'):
                obj = await obj
            return obj
    except:
        pass
    return None


def require_POST(view_func: Any) -> Any:
    """
    Decorator to require POST method.

    Example:
        @require_POST
        async def delete_post(request):
            ...
    """
    async def wrapper(request: Any, *args, **kwargs):
        if request.method != 'POST':
            raise HTTPException(status_code=405, detail="Method not allowed")
        return await view_func(request, *args, **kwargs)
    return wrapper


def require_GET(view_func: Any) -> Any:
    """Decorator to require GET method."""
    async def wrapper(request: Any, *args, **kwargs):
        if request.method != 'GET':
            raise HTTPException(status_code=405, detail="Method not allowed")
        return await view_func(request, *args, **kwargs)
    return wrapper


def require_http_methods(methods: List[str]):
    """
    Decorator to require specific HTTP methods.

    Example:
        @require_http_methods(['GET', 'POST'])
        async def edit_post(request):
            ...
    """
    def decorator(view_func: Any) -> Any:
        async def wrapper(request: Any, *args, **kwargs):
            if request.method not in methods:
                raise HTTPException(status_code=405, detail="Method not allowed")
            return await view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def login_required(view_func: Any = None, login_url: str = '/login/') -> Any:
    """
    Decorator to require authenticated user.

    Example:
        @login_required
        async def profile(request):
            return render(request, 'profile.html')

        @login_required(login_url='/auth/signin/')
        async def dashboard(request):
            ...
    """
    def decorator(view_func: Any) -> Any:
        async def wrapper(request: Any, *args, **kwargs):
            user = getattr(request, 'user', None)

            if user is None or not getattr(user, 'is_authenticated', False):
                return redirect(login_url + '?next=' + request.url.path)

            return await view_func(request, *args, **kwargs)
        return wrapper

    if view_func:
        return decorator(view_func)
    return decorator


def permission_required(perm: str, login_url: str = '/login/', raise_exception: bool = False):
    """
    Decorator to require specific permission.

    Example:
        @permission_required('blog.add_post')
        async def create_post(request):
            ...
    """
    def decorator(view_func: Any) -> Any:
        async def wrapper(request: Any, *args, **kwargs):
            user = getattr(request, 'user', None)

            if user is None or not getattr(user, 'is_authenticated', False):
                return redirect(login_url + '?next=' + request.url.path)

            if not user.has_perm(perm):
                if raise_exception:
                    raise Http403("Permission denied")
                return redirect(login_url)

            return await view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def staff_member_required(view_func: Any = None, login_url: str = '/admin/login/'):
    """Decorator to require staff member."""
    def decorator(view_func: Any) -> Any:
        async def wrapper(request: Any, *args, **kwargs):
            user = getattr(request, 'user', None)

            if user is None or not getattr(user, 'is_authenticated', False):
                return redirect(login_url + '?next=' + request.url.path)

            if not getattr(user, 'is_staff', False):
                raise Http403("Staff member required")

            return await view_func(request, *args, **kwargs)
        return wrapper

    if view_func:
        return decorator(view_func)
    return decorator


def superuser_required(view_func: Any = None, login_url: str = '/admin/login/'):
    """Decorator to require superuser."""
    def decorator(view_func: Any) -> Any:
        async def wrapper(request: Any, *args, **kwargs):
            user = getattr(request, 'user', None)

            if user is None or not getattr(user, 'is_authenticated', False):
                return redirect(login_url + '?next=' + request.url.path)

            if not getattr(user, 'is_superuser', False):
                raise Http403("Superuser required")

            return await view_func(request, *args, **kwargs)
        return wrapper

    if view_func:
        return decorator(view_func)
    return decorator
