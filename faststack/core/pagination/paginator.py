"""
FastStack Pagination System

Provides Django-compatible pagination with async-first design.
Supports both synchronous and asynchronous pagination patterns.

Features:
- Paginator and Page classes for sync operations
- AsyncPaginator and AsyncPage for fully async operations
- Support for lazy object lists (querysets, async generators)
- Graceful handling of invalid page numbers
- Orphan item handling for better UX
"""

from __future__ import annotations

import math
from typing import (
    Any,
    AsyncIterator,
    Generic,
    Iterable,
    Iterator,
    Sequence,
    TypeVar,
    Union,
    overload,
)

T = TypeVar("T")


class EmptyPage(Exception):
    """
    Exception raised when an invalid page is requested.

    This exception is raised when:
    - A page number is less than 1
    - A page number is greater than the total number of pages
    - The object list is empty and allow_empty_first_page is False

    Attributes:
        message: Human-readable error message
        page_number: The invalid page number that was requested
    """

    def __init__(self, message: str, page_number: int | None = None) -> None:
        """
        Initialize EmptyPage exception.

        Args:
            message: Error message
            page_number: The invalid page number (optional)
        """
        super().__init__(message)
        self.message = message
        self.page_number = page_number


class PageNotAnInteger(Exception):
    """
    Exception raised when a page number is not a valid integer.

    This exception is raised when:
    - A page value is not numeric (e.g., None, string, float)
    - A page value cannot be converted to an integer
    """

    def __init__(self, message: str, value: Any = None) -> None:
        """
        Initialize PageNotAnInteger exception.

        Args:
            message: Error message
            value: The invalid value that was provided
        """
        super().__init__(message)
        self.message = message
        self.value = value


class InvalidPage(Exception):
    """
    Base exception for all pagination errors.

    Both EmptyPage and PageNotAnInteger inherit from this exception,
    allowing for generic exception handling.
    """

    pass


class Page(Generic[T]):
    """
    Represents a single page of items from a paginated list.

    Provides navigation methods and index information for a page.
    Designed to be Django-compatible while being async-first.

    Attributes:
        object_list: The items on this page
        number: The 1-based page number
        paginator: The parent Paginator instance

    Example:
        ```python
        paginator = Paginator(items, per_page=10)
        page = paginator.page(1)

        if page.has_next():
            next_page = paginator.page(page.next_page_number())

        for item in page:
            print(item)
        ```
    """

    def __init__(
        self,
        object_list: Sequence[T],
        number: int,
        paginator: Paginator[T],
    ) -> None:
        """
        Initialize a Page instance.

        Args:
            object_list: Items on this page
            number: 1-based page number
            paginator: Parent Paginator instance
        """
        self._object_list = object_list
        self._number = number
        self._paginator = paginator

    @property
    def object_list(self) -> Sequence[T]:
        """Get the items on this page."""
        return self._object_list

    @property
    def items(self) -> Sequence[T]:
        """Alias for object_list for convenience."""
        return self._object_list

    @property
    def number(self) -> int:
        """Get the 1-based page number."""
        return self._number

    @property
    def paginator(self) -> Paginator[T]:
        """Get the parent Paginator instance."""
        return self._paginator

    def has_next(self) -> bool:
        """
        Check if there is a next page.

        Returns:
            True if there is a next page, False otherwise
        """
        return self._number < self._paginator.num_pages

    def has_previous(self) -> bool:
        """
        Check if there is a previous page.

        Returns:
            True if there is a previous page, False otherwise
        """
        return self._number > 1

    def has_other_pages(self) -> bool:
        """
        Check if there are other pages besides this one.

        Returns:
            True if there are other pages, False if this is the only page
        """
        return self.has_next() or self.has_previous()

    def next_page_number(self) -> int:
        """
        Get the next page number.

        Returns:
            The next page number

        Raises:
            EmptyPage: If there is no next page
        """
        if not self.has_next():
            raise EmptyPage(
                f"Page {self._number} has no next page",
                page_number=self._number + 1,
            )
        return self._number + 1

    def previous_page_number(self) -> int:
        """
        Get the previous page number.

        Returns:
            The previous page number

        Raises:
            EmptyPage: If there is no previous page
        """
        if not self.has_previous():
            raise EmptyPage(
                f"Page {self._number} has no previous page",
                page_number=self._number - 1,
            )
        return self._number - 1

    def start_index(self) -> int:
        """
        Get the 1-based index of the first item on this page.

        Returns:
            1-based index of the first item
        """
        if self._paginator.count == 0:
            return 0
        return (self._paginator.per_page * (self._number - 1)) + 1

    def end_index(self) -> int:
        """
        Get the 1-based index of the last item on this page.

        Returns:
            1-based index of the last item
        """
        if self._paginator.count == 0:
            return 0
        return min(
            self._paginator.per_page * self._number,
            self._paginator.count,
        )

    def __len__(self) -> int:
        """Return the number of items on this page."""
        return len(self._object_list)

    def __getitem__(self, index: int) -> T:
        """Get an item by index from this page."""
        return self._object_list[index]

    def __iter__(self) -> Iterator[T]:
        """Iterate over items on this page."""
        return iter(self._object_list)

    def __contains__(self, item: T) -> bool:
        """Check if an item is on this page."""
        return item in self._object_list

    def __repr__(self) -> str:
        """Return string representation of this page."""
        return f"<Page {self._number} of {self._paginator.num_pages}>"


class Paginator(Generic[T]):
    """
    Core paginator class for splitting sequences into pages.

    Provides Django-compatible pagination with support for:
    - Orphan item handling
    - Empty first page configuration
    - Lazy object lists (supports both sync and async count methods)

    Attributes:
        object_list: The items to paginate
        per_page: Number of items per page
        orphans: Minimum items on last page before merging with previous
        allow_empty_first_page: Whether to allow empty first page

    Example:
        ```python
        # Basic usage
        paginator = Paginator(items, per_page=10)
        page = paginator.page(1)

        # With orphans
        paginator = Paginator(items, per_page=10, orphans=2)

        # Get page safely (handles invalid numbers)
        page = paginator.get_page(999)  # Returns last page

        # Get page strictly (raises on invalid)
        page = paginator.page(999)  # Raises EmptyPage
        ```
    """

    def __init__(
        self,
        object_list: Sequence[T],
        per_page: int,
        orphans: int = 0,
        allow_empty_first_page: bool = True,
    ) -> None:
        """
        Initialize a Paginator instance.

        Args:
            object_list: Sequence of items to paginate
            per_page: Number of items per page (must be positive)
            orphans: Minimum items on last page. If last page has fewer
                items than this, they are merged with the previous page.
            allow_empty_first_page: If True, returns empty page for empty
                lists. If False, raises EmptyPage for empty lists.

        Raises:
            ValueError: If per_page is not positive
        """
        if per_page <= 0:
            raise ValueError("per_page must be a positive integer")

        self._object_list = object_list
        self._per_page = per_page
        self._orphans = orphans
        self._allow_empty_first_page = allow_empty_first_page
        self._count: int | None = None

    @property
    def object_list(self) -> Sequence[T]:
        """Get the object list being paginated."""
        return self._object_list

    @property
    def per_page(self) -> int:
        """Get the number of items per page."""
        return self._per_page

    @property
    def orphans(self) -> int:
        """Get the orphan threshold."""
        return self._orphans

    @property
    def allow_empty_first_page(self) -> bool:
        """Check if empty first page is allowed."""
        return self._allow_empty_first_page

    @property
    def count(self) -> int:
        """
        Get the total number of items across all pages.

        This property caches the count after first computation.

        Returns:
            Total number of items
        """
        if self._count is None:
            self._count = self._get_count()
        return self._count

    @property
    def total_items(self) -> int:
        """Alias for count for backward compatibility."""
        return self.count

    @property
    def total_pages(self) -> int:
        """Alias for num_pages for backward compatibility."""
        return self.num_pages

    async def acount(self) -> int:
        """
        Async version of count property.

        Use this when the object list might be a lazy async object
        that requires async count computation.

        Returns:
            Total number of items
        """
        if self._count is None:
            self._count = await self._get_count_async()
        return self._count

    def _get_count(self) -> int:
        """
        Compute the count of items.

        Handles both regular sequences and objects with a count() method.

        Returns:
            Number of items
        """
        # Check if object_list has a count() method that takes no arguments
        # (like Django QuerySet, not Python list.count(item))
        if hasattr(self._object_list, "count"):
            import inspect

            try:
                sig = inspect.signature(self._object_list.count)
                params = [p for p in sig.parameters.values() if p.default is inspect.Parameter.empty]
                # If count() takes no required arguments, call it
                if len(params) == 0:
                    count = self._object_list.count()
                    # Handle both sync and async count methods
                    if hasattr(count, "__await__"):
                        import asyncio

                        return asyncio.get_event_loop().run_until_complete(count)
                    return count
            except (ValueError, TypeError):
                # If we can't inspect, try calling without arguments
                pass
        return len(self._object_list)

    async def _get_count_async(self) -> int:
        """
        Async version of count computation.

        Returns:
            Number of items
        """
        # Check if object_list has an async count method
        if hasattr(self._object_list, "acount"):
            return await self._object_list.acount()
        # Check for regular count method that takes no arguments
        if hasattr(self._object_list, "count"):
            import inspect

            try:
                sig = inspect.signature(self._object_list.count)
                params = [p for p in sig.parameters.values() if p.default is inspect.Parameter.empty]
                # If count() takes no required arguments, call it
                if len(params) == 0:
                    count = self._object_list.count()
                    if hasattr(count, "__await__"):
                        return await count
                    return count
            except (ValueError, TypeError):
                pass
        return len(self._object_list)

    @property
    def num_pages(self) -> int:
        """
        Get the total number of pages.

        Returns:
            Total number of pages (minimum 1)
        """
        if self.count == 0:
            if self._allow_empty_first_page:
                return 1
            return 0

        hits = max(1, self.count - self._orphans)
        return int(math.ceil(hits / self._per_page))

    @property
    def page_range(self) -> range:
        """
        Get a range of page numbers (1-based).

        Returns:
            Range from 1 to num_pages inclusive
        """
        return range(1, self.num_pages + 1)

    def validate_number(self, number: int | str) -> int:
        """
        Validate and normalize a page number.

        Converts string numbers to integers and validates bounds.

        Args:
            number: Page number (int or string)

        Returns:
            Validated integer page number

        Raises:
            PageNotAnInteger: If number cannot be converted to int
            EmptyPage: If number is out of valid range
        """
        try:
            number = int(number)
        except (TypeError, ValueError) as e:
            raise PageNotAnInteger(
                f"Page number must be an integer, got {number!r}",
                value=number,
            ) from e

        if number < 1:
            raise EmptyPage(
                f"Page number {number} is less than 1",
                page_number=number,
            )

        if number > self.num_pages:
            if number == 1 and self._allow_empty_first_page:
                return 1
            raise EmptyPage(
                f"Page {number} of {self.num_pages} does not exist",
                page_number=number,
            )

        return number

    def page(self, number: int | str) -> Page[T]:
        """
        Get a page by number (strict).

        Returns the requested page, raising an exception if the
        page number is invalid.

        Args:
            number: Page number (1-based, can be string)

        Returns:
            Page instance for the requested page

        Raises:
            PageNotAnInteger: If number is not a valid integer
            EmptyPage: If page does not exist
        """
        number = self.validate_number(number)
        bottom = (number - 1) * self._per_page
        top = bottom + self._per_page

        # Handle orphans on last page
        if top + self._orphans >= self.count:
            top = self.count

        return Page(self._object_list[bottom:top], number, self)

    def get_page(self, number: int | str) -> Page[T]:
        """
        Get a page by number (graceful).

        Returns the requested page, handling invalid page numbers
        gracefully by returning the first or last valid page.

        Args:
            number: Page number (1-based, can be string)

        Returns:
            Page instance (first or last page for invalid numbers)
        """
        try:
            number = self.validate_number(number)
        except PageNotAnInteger:
            number = 1
        except EmptyPage:
            number = self.num_pages if self.num_pages > 0 else 1

        if number < 1:
            number = 1
        elif number > self.num_pages:
            number = self.num_pages if self.num_pages > 0 else 1

        return self.page(number)

    def __len__(self) -> int:
        """Return the total number of pages."""
        return self.num_pages

    def __iter__(self) -> Iterator[Page[T]]:
        """Iterate over all pages."""
        for page_num in self.page_range:
            yield self.page(page_num)

    def __repr__(self) -> str:
        """Return string representation of this paginator."""
        return f"<Paginator: {self.count} items, {self.num_pages} pages>"


class AsyncPage(Generic[T]):
    """
    Async variant of Page for fully async pagination.

    Provides the same interface as Page but with async iteration
    support and async property access.

    Example:
        ```python
        paginator = AsyncPaginator(items, per_page=10)
        page = await paginator.page(1)

        async for item in page:
            print(item)
        ```
    """

    def __init__(
        self,
        object_list: Sequence[T],
        number: int,
        paginator: AsyncPaginator[T],
    ) -> None:
        """
        Initialize an AsyncPage instance.

        Args:
            object_list: Items on this page
            number: 1-based page number
            paginator: Parent AsyncPaginator instance
        """
        self._object_list = object_list
        self._number = number
        self._paginator = paginator

    @property
    def object_list(self) -> Sequence[T]:
        """Get the items on this page."""
        return self._object_list

    @property
    def number(self) -> int:
        """Get the 1-based page number."""
        return self._number

    @property
    def paginator(self) -> AsyncPaginator[T]:
        """Get the parent AsyncPaginator instance."""
        return self._paginator

    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self._number < self._paginator._num_pages

    def has_previous(self) -> bool:
        """Check if there is a previous page."""
        return self._number > 1

    def has_other_pages(self) -> bool:
        """Check if there are other pages besides this one."""
        return self.has_next() or self.has_previous()

    def next_page_number(self) -> int:
        """Get the next page number, raises EmptyPage if none."""
        if not self.has_next():
            raise EmptyPage(
                f"Page {self._number} has no next page",
                page_number=self._number + 1,
            )
        return self._number + 1

    def previous_page_number(self) -> int:
        """Get the previous page number, raises EmptyPage if none."""
        if not self.has_previous():
            raise EmptyPage(
                f"Page {self._number} has no previous page",
                page_number=self._number - 1,
            )
        return self._number - 1

    async def start_index(self) -> int:
        """Get the 1-based index of the first item on this page."""
        count = await self._paginator.acount()
        if count == 0:
            return 0
        return (self._paginator.per_page * (self._number - 1)) + 1

    async def end_index(self) -> int:
        """Get the 1-based index of the last item on this page."""
        count = await self._paginator.acount()
        if count == 0:
            return 0
        return min(
            self._paginator.per_page * self._number,
            count,
        )

    def __len__(self) -> int:
        """Return the number of items on this page."""
        return len(self._object_list)

    def __getitem__(self, index: int) -> T:
        """Get an item by index from this page."""
        return self._object_list[index]

    def __iter__(self) -> Iterator[T]:
        """Iterate over items on this page (sync)."""
        return iter(self._object_list)

    async def __aiter__(self) -> AsyncIterator[T]:
        """Iterate over items on this page (async)."""
        for item in self._object_list:
            yield item

    def __contains__(self, item: T) -> bool:
        """Check if an item is on this page."""
        return item in self._object_list

    def __repr__(self) -> str:
        """Return string representation of this page."""
        return f"<AsyncPage {self._number} of {self._paginator._num_pages or '?'}>"


class AsyncPaginator(Generic[T]):
    """
    Async variant of Paginator for fully async pagination.

    Provides the same interface as Paginator but with async methods
    for count computation and page retrieval.

    Designed for use with async ORMs and database connections.

    Example:
        ```python
        # With async queryset
        paginator = AsyncPaginator(await async_queryset, per_page=10)
        page = await paginator.page(1)

        # Or with lazy async count
        paginator = AsyncPaginator(lazy_queryset, per_page=10)
        count = await paginator.acount()
        page = await paginator.aget_page(1)
        ```
    """

    def __init__(
        self,
        object_list: Sequence[T],
        per_page: int,
        orphans: int = 0,
        allow_empty_first_page: bool = True,
    ) -> None:
        """
        Initialize an AsyncPaginator instance.

        Args:
            object_list: Sequence of items to paginate
            per_page: Number of items per page (must be positive)
            orphans: Minimum items on last page
            allow_empty_first_page: If True, allows empty first page
        """
        if per_page <= 0:
            raise ValueError("per_page must be a positive integer")

        self._object_list = object_list
        self._per_page = per_page
        self._orphans = orphans
        self._allow_empty_first_page = allow_empty_first_page
        self._count: int | None = None
        self._num_pages: int | None = None

    @property
    def object_list(self) -> Sequence[T]:
        """Get the object list being paginated."""
        return self._object_list

    @property
    def per_page(self) -> int:
        """Get the number of items per page."""
        return self._per_page

    @property
    def orphans(self) -> int:
        """Get the orphan threshold."""
        return self._orphans

    @property
    def allow_empty_first_page(self) -> bool:
        """Check if empty first page is allowed."""
        return self._allow_empty_first_page

    async def acount(self) -> int:
        """
        Get the total number of items (async).

        Returns:
            Total number of items
        """
        if self._count is None:
            self._count = await self._get_count_async()
        return self._count

    async def _get_count_async(self) -> int:
        """Compute count asynchronously."""
        # Check for async count method
        if hasattr(self._object_list, "acount"):
            return await self._object_list.acount()
        # Check for regular count method that takes no arguments
        if hasattr(self._object_list, "count"):
            import inspect

            try:
                sig = inspect.signature(self._object_list.count)
                params = [p for p in sig.parameters.values() if p.default is inspect.Parameter.empty]
                # If count() takes no required arguments, call it
                if len(params) == 0:
                    count = self._object_list.count()
                    if hasattr(count, "__await__"):
                        return await count
                    return count
            except (ValueError, TypeError):
                pass
        return len(self._object_list)

    async def anum_pages(self) -> int:
        """
        Get the total number of pages (async).

        Returns:
            Total number of pages (minimum 1)
        """
        if self._num_pages is None:
            count = await self.acount()
            if count == 0:
                if self._allow_empty_first_page:
                    self._num_pages = 1
                else:
                    self._num_pages = 0
            else:
                hits = max(1, count - self._orphans)
                self._num_pages = int(math.ceil(hits / self._per_page))
        return self._num_pages

    async def apage_range(self) -> range:
        """
        Get a range of page numbers (async).

        Returns:
            Range from 1 to num_pages inclusive
        """
        num_pages = await self.anum_pages()
        return range(1, num_pages + 1)

    async def validate_number(self, number: int | str) -> int:
        """
        Validate and normalize a page number (async).

        Args:
            number: Page number (int or string)

        Returns:
            Validated integer page number

        Raises:
            PageNotAnInteger: If number cannot be converted to int
            EmptyPage: If number is out of valid range
        """
        try:
            number = int(number)
        except (TypeError, ValueError) as e:
            raise PageNotAnInteger(
                f"Page number must be an integer, got {number!r}",
                value=number,
            ) from e

        if number < 1:
            raise EmptyPage(
                f"Page number {number} is less than 1",
                page_number=number,
            )

        num_pages = await self.anum_pages()
        if number > num_pages:
            if number == 1 and self._allow_empty_first_page:
                return 1
            raise EmptyPage(
                f"Page {number} of {num_pages} does not exist",
                page_number=number,
            )

        return number

    async def apage(self, number: int | str) -> AsyncPage[T]:
        """
        Get a page by number (strict, async).

        Args:
            number: Page number (1-based, can be string)

        Returns:
            AsyncPage instance for the requested page

        Raises:
            PageNotAnInteger: If number is not a valid integer
            EmptyPage: If page does not exist
        """
        number = await self.validate_number(number)
        count = await self.acount()

        bottom = (number - 1) * self._per_page
        top = bottom + self._per_page

        # Handle orphans on last page
        if top + self._orphans >= count:
            top = count

        return AsyncPage(self._object_list[bottom:top], number, self)

    async def aget_page(self, number: int | str) -> AsyncPage[T]:
        """
        Get a page by number (graceful, async).

        Handles invalid page numbers by returning first or last valid page.

        Args:
            number: Page number (1-based, can be string)

        Returns:
            AsyncPage instance (first or last page for invalid numbers)
        """
        num_pages = await self.anum_pages()

        try:
            number = await self.validate_number(number)
        except PageNotAnInteger:
            number = 1
        except EmptyPage:
            number = num_pages if num_pages > 0 else 1

        if number < 1:
            number = 1
        elif number > num_pages:
            number = num_pages if num_pages > 0 else 1

        return await self.apage(number)

    async def __aiter__(self) -> AsyncIterator[AsyncPage[T]]:
        """Iterate over all pages asynchronously."""
        page_range = await self.apage_range()
        for page_num in page_range:
            yield await self.apage(page_num)

    def __repr__(self) -> str:
        """Return string representation of this paginator."""
        return f"<AsyncPaginator: per_page={self._per_page}>"


# Type alias for backward compatibility
PageLike = Union[Page[T], AsyncPage[T]]
PaginatorLike = Union[Paginator[T], AsyncPaginator[T]]
