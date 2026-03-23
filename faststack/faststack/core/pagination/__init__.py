"""
FastStack Pagination Framework

Provides Django-like pagination for lists and querysets.

Example:
    from faststack.core.pagination import Paginator, Page

    # Create paginator
    paginator = Paginator(queryset, per_page=20)

    # Get specific page
    page = paginator.page(1)

    # In template
    {% for item in page %}
        {{ item }}
    {% endfor %}

    # Pagination links
    {% if page.has_previous %}
        <a href="?page={{ page.previous_page_number }}">Previous</a>
    {% endif %}
"""

from .paginator import Paginator, Page, EmptyPage, PageNotAnInteger
from .utils import paginate, get_page

__all__ = [
    'Paginator', 'Page', 'EmptyPage', 'PageNotAnInteger',
    'paginate', 'get_page',
]
