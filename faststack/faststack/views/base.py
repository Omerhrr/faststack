"""Base View Classes"""
from typing import Callable, Any
from functools import wraps


class View:
    """Base class for all views."""
    
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
    template_name = None
    
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.request = None
    
    @classmethod
    def as_view(cls, **initkwargs) -> Callable:
        async def view(request, **kwargs):
            self = cls(**initkwargs)
            self.request = request
            self.args = ()
            self.kwargs = kwargs
            return await self.dispatch(request, **kwargs)
        view.view_class = cls
        return view
    
    async def dispatch(self, request, **kwargs):
        method = request.method.lower()
        if method not in self.http_method_names:
            from starlette.exceptions import HTTPException
            raise HTTPException(405)
        handler = getattr(self, method, None)
        if handler is None:
            from starlette.exceptions import HTTPException
            raise HTTPException(405)
        return await handler(request, **kwargs)
    
    def render(self, context=None, template_name=None):
        from faststack.app import get_templates
        template = template_name or self.template_name
        templates = get_templates()
        ctx = context or {}
        ctx['request'] = self.request
        return templates.TemplateResponse(template, ctx)
    
    def redirect(self, url, permanent=False):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url, status_code=301 if permanent else 302)


class TemplateView(View):
    """View that renders a template."""
    
    async def get(self, request, **kwargs):
        return self.render({})
    
    async def post(self, request, **kwargs):
        return await self.get(request, **kwargs)


class RedirectView(View):
    """View that redirects."""
    
    url = None
    permanent = False
    
    async def get(self, request, **kwargs):
        url = self.get_redirect_url(**kwargs)
        if url is None:
            from starlette.exceptions import HTTPException
            raise HTTPException(410)
        return self.redirect(url, self.permanent)
    
    def get_redirect_url(self, **kwargs):
        return self.url


def as_view(view_class, **initkwargs):
    return view_class.as_view(**initkwargs)
