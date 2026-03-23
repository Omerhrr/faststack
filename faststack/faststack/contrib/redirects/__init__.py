"""
FastStack Redirects - URL redirect management.

Example:
    from faststack.contrib.redirects import Redirect

    # Create redirect
    await Redirect.create(
        old_path='/old-page/',
        new_path='/new-page/',
        is_permanent=True
    )

    # Middleware handles redirects automatically
    app.add_middleware(RedirectFallbackMiddleware)
"""

from .models import Redirect
from .middleware import RedirectFallbackMiddleware

__all__ = [
    'Redirect',
    'RedirectFallbackMiddleware',
]
