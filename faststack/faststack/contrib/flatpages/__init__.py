"""
FastStack Flatpages - Simple CMS for static content.

Example:
    from faststack.contrib.flatpages import FlatPage

    # Create a flatpage
    await FlatPage.create(
        url='/about/',
        title='About Us',
        content='<h1>About</h1><p>Our story...</p>'
    )

    # In routes
    app.include_router(flatpages_router)
"""

from .models import FlatPage
from .middleware import FlatpageFallbackMiddleware
from .views import flatpage, flatpages_router

__all__ = [
    'FlatPage',
    'FlatpageFallbackMiddleware',
    'flatpage',
    'flatpages_router',
]
