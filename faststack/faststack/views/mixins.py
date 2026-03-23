"""View Mixins"""


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
