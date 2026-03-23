"""
Pagination utilities and helpers.
"""

from typing import Any, Optional, TypeVar, Sequence
from .paginator import Paginator, Page, EmptyPage, PageNotAnInteger

T = TypeVar('T')


def paginate(
    object_list: Sequence[T],
    per_page: int = 20,
    page: int = 1,
    orphans: int = 0,
    allow_empty_first_page: bool = True
) -> Page[T]:
    """
    Convenience function to paginate a list.

    Args:
        object_list: Items to paginate
        per_page: Items per page
        page: Page number to get
        orphans: Minimum items on last page
        allow_empty_first_page: Allow empty first page

    Returns:
        Page object

    Example:
        page = paginate(items, per_page=10, page=request.args.get('page', 1))
    """
    paginator = Paginator(object_list, per_page, orphans, allow_empty_first_page)
    return paginator.page(page)


def get_page(
    object_list: Sequence[T],
    page_number: Any,
    per_page: int = 20,
    orphans: int = 0,
    allow_empty_first_page: bool = True
) -> Page[T]:
    """
    Get a page with error handling.

    Returns first page if page_number is invalid,
    or last page if page_number is too high.

    Args:
        object_list: Items to paginate
        page_number: Page number (can be string)
        per_page: Items per page
        orphans: Minimum items on last page
        allow_empty_first_page: Allow empty first page

    Returns:
        Page object
    """
    paginator = Paginator(object_list, per_page, orphans, allow_empty_first_page)

    try:
        return paginator.page(page_number)
    except PageNotAnInteger:
        # Return first page
        return paginator.page(1)
    except EmptyPage:
        # Return last page
        return paginator.page(paginator.num_pages)


class PaginationMeta:
    """
    Pagination metadata for API responses.

    Useful for building REST API responses with pagination info.

    Example:
        {
            'count': 100,
            'next': 'https://api.example.com/items?page=3',
            'previous': 'https://api.example.com/items?page=1',
            'results': [...]
        }
    """

    def __init__(
        self,
        page: Page,
        request_url: Optional[str] = None,
        page_param: str = 'page'
    ):
        """
        Initialize pagination metadata.

        Args:
            page: Page object
            request_url: Base URL for generating links
            page_param: Query parameter name for page number
        """
        self.page = page
        self.paginator = page.paginator
        self.request_url = request_url
        self.page_param = page_param

    def _build_url(self, page_number: int) -> str:
        """Build URL for a specific page."""
        if not self.request_url:
            return ''

        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

        parsed = urlparse(self.request_url)
        query_params = parse_qs(parsed.query)
        query_params[self.page_param] = [str(page_number)]

        new_query = urlencode(query_params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    @property
    def count(self) -> int:
        """Total number of items."""
        return self.paginator.count

    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        return self.paginator.num_pages

    @property
    def current_page(self) -> int:
        """Current page number."""
        return self.page.number

    @property
    def next_url(self) -> Optional[str]:
        """URL for next page."""
        if self.page.has_next():
            return self._build_url(self.page.next_page_number())
        return None

    @property
    def previous_url(self) -> Optional[str]:
        """URL for previous page."""
        if self.page.has_previous():
            return self._build_url(self.page.previous_page_number())
        return None

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page.has_next()

    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.page.has_previous()

    @property
    def start_index(self) -> int:
        """1-based index of first item on this page."""
        return self.page.start_index()

    @property
    def end_index(self) -> int:
        """1-based index of last item on this page."""
        return self.page.end_index()

    def to_dict(self) -> dict:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with pagination metadata
        """
        return {
            'count': self.count,
            'total_pages': self.total_pages,
            'current_page': self.current_page,
            'has_next': self.has_next,
            'has_previous': self.has_previous,
            'next': self.next_url,
            'previous': self.previous_url,
        }

    def api_response(self, results: Any = None) -> dict:
        """
        Build standard API pagination response.

        Args:
            results: Results list (defaults to page items)

        Returns:
            Dictionary ready for JSON response
        """
        if results is None:
            results = list(self.page)

        return {
            'count': self.count,
            'next': self.next_url,
            'previous': self.previous_url,
            'results': results,
        }


class InfiniteScroll:
    """
    Infinite scroll pagination helper.

    Simplifies infinite scroll UI patterns.

    Example:
        scroll = InfiniteScroll(items, per_page=20)
        page = scroll.get_page(last_id=request.args.get('last_id'))
    """

    def __init__(
        self,
        object_list: Sequence[T],
        per_page: int = 20,
        id_field: str = 'id'
    ):
        """
        Initialize infinite scroll.

        Args:
            object_list: Items to paginate
            per_page: Items per page
            id_field: Field to use for cursor
        """
        self.object_list = object_list
        self.per_page = per_page
        self.id_field = id_field

    def get_page(self, last_id: Any = None) -> dict:
        """
        Get a page for infinite scroll.

        Args:
            last_id: ID of last item from previous page

        Returns:
            Dictionary with items and last_id
        """
        items = []
        last_id_value = None

        # Filter items after last_id
        started = last_id is None
        count = 0

        for item in self.object_list:
            if not started:
                if getattr(item, self.id_field) == last_id:
                    started = True
                continue

            if count >= self.per_page:
                break

            items.append(item)
            last_id_value = getattr(item, self.id_field)
            count += 1

        has_more = count == self.per_page

        return {
            'items': items,
            'last_id': last_id_value,
            'has_more': has_more,
        }
