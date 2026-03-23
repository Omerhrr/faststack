"""
Paginator implementation with Django-like API.
"""

from typing import Any, Generic, List, Optional, Sequence, TypeVar, Union, Iterator
from math import ceil

T = TypeVar('T')


class EmptyPage(Exception):
    """Raised when requesting an empty page."""
    pass


class PageNotAnInteger(Exception):
    """Raised when page parameter is not an integer."""
    pass


class Page(Generic[T]):
    """
    A single page of results.

    Provides attributes and methods for accessing page contents
    and generating pagination links.

    Example:
        page = paginator.page(1)
        print(page.object_list)  # Items on this page
        print(page.number)       # Page number
        print(page.has_next())   # Has next page?
    """

    def __init__(
        self,
        object_list: Sequence[T],
        number: int,
        paginator: 'Paginator'
    ):
        """
        Initialize Page.

        Args:
            object_list: Items on this page
            number: Page number (1-indexed)
            paginator: Parent Paginator instance
        """
        self.object_list = object_list
        self.number = number
        self.paginator = paginator

    def __repr__(self) -> str:
        return f"<Page {self.number} of {self.paginator.num_pages}>"

    def __len__(self) -> int:
        return len(self.object_list)

    def __getitem__(self, index: int) -> T:
        return self.object_list[index]

    def __iter__(self) -> Iterator[T]:
        return iter(self.object_list)

    def __bool__(self) -> bool:
        return len(self.object_list) > 0

    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.number < self.paginator.num_pages

    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.number > 1

    def has_other_pages(self) -> bool:
        """Check if there are other pages besides this one."""
        return self.has_next() or self.has_previous()

    def next_page_number(self) -> int:
        """Get next page number. Raises EmptyPage if no next page."""
        if not self.has_next():
            raise EmptyPage("No next page")
        return self.number + 1

    def previous_page_number(self) -> int:
        """Get previous page number. Raises EmptyPage if no previous page."""
        if not self.has_previous():
            raise EmptyPage("No previous page")
        return self.number - 1

    def start_index(self) -> int:
        """
        Get 1-based index of first item on this page.

        Example: For page 2 with 10 items per page, returns 11.
        """
        if self.paginator.count == 0:
            return 0
        return (self.paginator.per_page * (self.number - 1)) + 1

    def end_index(self) -> int:
        """
        Get 1-based index of last item on this page.

        Example: For page 2 with 10 items per page, returns 20.
        """
        if self.number == self.paginator.num_pages:
            return self.paginator.count
        return self.number * self.paginator.per_page

    @property
    def next_page_url(self) -> Optional[str]:
        """URL for next page (if configured)."""
        return None

    @property
    def previous_page_url(self) -> Optional[str]:
        """URL for previous page (if configured)."""
        return None


class Paginator(Generic[T]):
    """
    Django-like Paginator for splitting sequences into pages.

    Example:
        # Basic usage
        paginator = Paginator(items, per_page=20)
        page = paginator.page(1)

        # With async queryset
        paginator = Paginator(await Model.all(), per_page=10)

        # Handling errors
        try:
            page = paginator.page(1)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)
    """

    # Default number of adjacent pages to show in pagination
    orphans: int = 0

    def __init__(
        self,
        object_list: Union[Sequence[T], Any],
        per_page: int,
        orphans: int = 0,
        allow_empty_first_page: bool = True
    ):
        """
        Initialize Paginator.

        Args:
            object_list: List, tuple, queryset, or any sequence to paginate
            per_page: Number of items per page
            orphans: Minimum number of items on last page (merge into previous if less)
            allow_empty_first_page: Whether to allow empty first page
        """
        self.object_list = object_list
        self.per_page = per_page
        self.orphans = orphans
        self.allow_empty_first_page = allow_empty_first_page

        # Validate per_page
        if per_page <= 0:
            raise ValueError("per_page must be a positive integer")

        # Compute count
        self._count = self._get_count()

    def __repr__(self) -> str:
        return f"<Paginator: {self.count} items, {self.num_pages} pages>"

    def __len__(self) -> int:
        return self.num_pages

    def __iter__(self) -> Iterator[Page[T]]:
        for i in range(1, self.num_pages + 1):
            yield self.page(i)

    def _get_count(self) -> int:
        """Get total count of items."""
        if hasattr(self.object_list, 'count'):
            # Queryset-like object with count method
            count = self.object_list.count()
            if callable(count):
                # async count method - return placeholder
                return 0
            return count
        return len(self.object_list)

    @property
    def count(self) -> int:
        """Total number of items across all pages."""
        return self._count

    @property
    def num_pages(self) -> int:
        """Total number of pages."""
        if self.count == 0:
            return 1 if self.allow_empty_first_page else 0

        hits = max(0, self.count - self.orphans)
        return ceil(hits / self.per_page)

    @property
    def page_range(self) -> range:
        """Range of page numbers (1-indexed)."""
        return range(1, self.num_pages + 1)

    def page(self, number: int) -> Page[T]:
        """
        Get a specific page.

        Args:
            number: Page number (1-indexed)

        Returns:
            Page object

        Raises:
            PageNotAnInteger: If number is not an integer
            EmptyPage: If page doesn't exist
        """
        number = self.validate_number(number)
        return self._get_page(number)

    def validate_number(self, number: Any) -> int:
        """
        Validate and return a page number.

        Args:
            number: Page number to validate

        Returns:
            Validated page number

        Raises:
            PageNotAnInteger: If number is not an integer
            EmptyPage: If page doesn't exist
        """
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise PageNotAnInteger("Page number is not an integer")

        if number < 1:
            raise EmptyPage("Page number is less than 1")

        if number > self.num_pages:
            if number == 1 and self.allow_empty_first_page:
                return number
            raise EmptyPage(f"Page {number} of {self.num_pages} does not exist")

        return number

    def _get_page(self, number: int) -> Page[T]:
        """
        Internal method to get a page's object list.

        Args:
            number: Validated page number

        Returns:
            Page object
        """
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page

        # Handle orphans on last page
        if top + self.orphans >= self.count:
            top = self.count

        # Get slice
        if hasattr(self.object_list, 'offset') and hasattr(self.object_list, 'limit'):
            # Queryset-like object with offset/limit
            page_list = self.object_list.offset(bottom).limit(top - bottom)
        elif hasattr(self.object_list, '__getitem__'):
            # Sliceable sequence
            page_list = self.object_list[bottom:top]
        else:
            raise TypeError("object_list must be sliceable or have offset/limit methods")

        return Page(page_list, number, self)

    def get_elided_page_range(
        self,
        number: int,
        on_each_side: int = 3,
        on_ends: int = 2
    ) -> List[Union[int, str]]:
        """
        Get page range with ellipsis for large page counts.

        Example:
            For 10 pages with on_each_side=2, on_ends=1:
            [1, 2, '…', 4, 5, 6, '…', 9, 10]

        Args:
            number: Current page number
            on_each_side: Pages to show on each side of current
            on_ends: Pages to show at start and end

        Returns:
            List of page numbers and '…' for gaps
        """
        number = self.validate_number(number)

        if self.num_pages <= (on_each_side + on_ends) * 2:
            return list(self.page_range)

        result = []

        # Start pages
        start_pages = list(range(1, on_ends + 1))

        # End pages
        end_pages = list(range(self.num_pages - on_ends + 1, self.num_pages + 1))

        # Pages around current
        left = max(on_ends + 1, number - on_each_side)
        right = min(self.num_pages - on_ends, number + on_each_side)

        middle_pages = list(range(left, right + 1))

        # Build result
        result.extend(start_pages)

        if left > on_ends + 1:
            result.append('…')

        result.extend(middle_pages)

        if right < self.num_pages - on_ends:
            result.append('…')

        result.extend(end_pages)

        return result

    # Async support methods

    async def aget_count(self) -> int:
        """Async get count for async querysets."""
        if hasattr(self.object_list, 'count'):
            count = self.object_list.count()
            if callable(count):
                # Async count
                return await count()
            return count
        return len(self.object_list)

    async def apage(self, number: int) -> Page[T]:
        """Async get a page for async querysets."""
        number = self.validate_number(number)
        return await self._aget_page(number)

    async def _aget_page(self, number: int) -> Page[T]:
        """Internal async method to get a page."""
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page

        if top + self.orphans >= self.count:
            top = self.count

        # Get slice for async queryset
        if hasattr(self.object_list, 'aoffset') and hasattr(self.object_list, 'alimit'):
            page_list = await self.object_list.aoffset(bottom).alimit(top - bottom)
        elif hasattr(self.object_list, 'offset') and hasattr(self.object_list, 'limit'):
            # Try sync methods
            page_list = self.object_list.offset(bottom).limit(top - bottom)
        elif hasattr(self.object_list, '__getitem__'):
            page_list = self.object_list[bottom:top]
        else:
            raise TypeError("object_list must support slicing or async offset/limit")

        return Page(page_list, number, self)


class AsyncPaginator(Paginator):
    """
    Async-aware Paginator for database querysets.

    Example:
        paginator = AsyncPaginator(queryset, per_page=20)
        page = await paginator.page(1)
    """

    async def page(self, number: int) -> Page:  # type: ignore
        """Async get a page."""
        return await self.apage(number)


class CursorPaginator(Generic[T]):
    """
    Cursor-based pagination for efficient large dataset navigation.

    Unlike offset-based pagination, cursor pagination uses a "cursor"
    (typically an ID or timestamp) to navigate, which is more efficient
    for large datasets and doesn't suffer from "missing items" issues
    when items are added/removed during pagination.

    Example:
        paginator = CursorPaginator(queryset, ordering='-created_at')
        page = await paginator.first_page()
        cursor = page.cursor  # Pass this to get next page
        next_page = await paginator.page(cursor)
    """

    def __init__(
        self,
        object_list: Any,
        per_page: int = 20,
        ordering: str = 'id',
        cursor_field: Optional[str] = None
    ):
        """
        Initialize CursorPaginator.

        Args:
            object_list: Queryset or sequence to paginate
            per_page: Items per page
            ordering: Field to order by (prefix with '-' for descending)
            cursor_field: Field to use for cursor (defaults to ordering field)
        """
        self.object_list = object_list
        self.per_page = per_page
        self.ordering = ordering
        self.cursor_field = cursor_field or ordering.lstrip('-')
        self.descending = ordering.startswith('-')

    def _get_cursor_value(self, obj: Any) -> Any:
        """Get cursor value from object."""
        return getattr(obj, self.cursor_field)

    def first_page(self) -> 'CursorPage':
        """Get the first page."""
        return self._get_page(cursor=None)

    def page(self, cursor: Any = None) -> 'CursorPage':
        """
        Get page by cursor.

        Args:
            cursor: Cursor value from previous page's next_cursor
        """
        return self._get_page(cursor)

    def _get_page(self, cursor: Any = None) -> 'CursorPage':
        """Internal method to get a cursor page."""
        queryset = self.object_list

        # Apply ordering
        if self.descending:
            queryset = sorted(queryset, key=lambda x: getattr(x, self.cursor_field), reverse=True)
        else:
            queryset = sorted(queryset, key=lambda x: getattr(x, self.cursor_field))

        # Filter by cursor
        if cursor is not None:
            for i, obj in enumerate(queryset):
                if self._get_cursor_value(obj) == cursor:
                    if self.descending:
                        queryset = queryset[:i]  # Items before cursor
                    else:
                        queryset = queryset[i+1:]  # Items after cursor
                    break

        # Get page items
        items = queryset[:self.per_page]
        has_next = len(queryset) > self.per_page
        next_cursor = None

        if items and has_next:
            next_cursor = self._get_cursor_value(items[-1])

        return CursorPage(
            items,
            per_page=self.per_page,
            has_next=has_next,
            has_previous=cursor is not None,
            next_cursor=next_cursor,
            previous_cursor=cursor
        )


class CursorPage(Generic[T]):
    """Page for cursor-based pagination."""

    def __init__(
        self,
        object_list: Sequence[T],
        per_page: int,
        has_next: bool,
        has_previous: bool,
        next_cursor: Any = None,
        previous_cursor: Any = None
    ):
        self.object_list = object_list
        self.per_page = per_page
        self.has_next = has_next
        self.has_previous = has_previous
        self.next_cursor = next_cursor
        self.previous_cursor = previous_cursor

    def __repr__(self) -> str:
        return f"<CursorPage: {len(self.object_list)} items>"

    def __len__(self) -> int:
        return len(self.object_list)

    def __iter__(self) -> Iterator[T]:
        return iter(self.object_list)

    def __getitem__(self, index: int) -> T:
        return self.object_list[index]
