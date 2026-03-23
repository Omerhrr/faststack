"""View Mixins"""

from typing import Any, List


class LoginRequiredMixin:
    """Requires user to be logged in."""
    
    login_url = "/login/"
    
    async def dispatch(self, request, **kwargs):
        user = getattr(request, 'user', None)
        if user is None or not getattr(user, 'is_authenticated', False):
            from starlette.exceptions import HTTPException
            raise HTTPException(401)
        return await super().dispatch(request, **kwargs)


class PermissionRequiredMixin:
    """Requires specific permissions."""
    
    permission_required = None
    
    async def dispatch(self, request, **kwargs):
        user = getattr(request, 'user', None)
        if user is None:
            from starlette.exceptions import HTTPException
            raise HTTPException(401)
        perms = getattr(user, 'permissions', set())
        if self.permission_required not in perms:
            from starlette.exceptions import HTTPException
            raise HTTPException(403)
        return await super().dispatch(request, **kwargs)


class StaffRequiredMixin:
    """Requires user to be staff."""
    
    async def dispatch(self, request, **kwargs):
        user = getattr(request, 'user', None)
        if user is None or not getattr(user, 'is_staff', False):
            from starlette.exceptions import HTTPException
            raise HTTPException(403)
        return await super().dispatch(request, **kwargs)


class SuperuserRequiredMixin:
    """Requires user to be superuser."""
    
    async def dispatch(self, request, **kwargs):
        user = getattr(request, 'user', None)
        if user is None or not getattr(user, 'is_superuser', getattr(user, 'is_admin', False)):
            from starlette.exceptions import HTTPException
            raise HTTPException(403)
        return await super().dispatch(request, **kwargs)


class PaginateMixin:
    """
    Mixin for adding pagination to views.
    
    Provides pagination functionality for list views.
    """
    
    paginate_by: int = 25
    paginate_orphans: int = 0
    page_kwarg: str = 'page'
    
    def get_paginate_by(self, request) -> int:
        """Get the number of items per page."""
        return self.paginate_by
    
    def get_paginate_orphans(self) -> int:
        """Get the number of orphans allowed."""
        return self.paginate_orphans
    
    def get_page_kwarg(self) -> str:
        """Get the page query parameter name."""
        return self.page_kwarg
    
    def paginate_queryset(self, queryset: Any, page_size: int) -> tuple:
        """
        Paginate a queryset.
        
        Args:
            queryset: The queryset to paginate
            page_size: Number of items per page
            
        Returns:
            Tuple of (paginator, page, object_list, is_paginated)
        """
        from ..core.pagination import Paginator, EmptyPage, PageNotAnInteger
        
        paginator = Paginator(queryset, page_size, orphans=self.get_paginate_orphans())
        
        page_kwarg = self.get_page_kwarg()
        page_num = getattr(self, 'request', None)
        if page_num:
            page_num = getattr(page_num, 'query_params', {}).get(page_kwarg, 1)
        else:
            page_num = 1
        
        try:
            page = paginator.page(page_num)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)
        
        return (paginator, page, page.object_list, page.has_other_pages())
