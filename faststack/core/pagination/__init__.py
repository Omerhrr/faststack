"""
FastStack Pagination Module

Provides Django-compatible pagination with async-first design.

Classes:
    Paginator: Core paginator for splitting sequences into pages
    Page: Represents a single page of items
    EmptyPage: Exception for invalid page requests
    PageNotAnInteger: Exception for non-integer page numbers
    InvalidPage: Base exception for pagination errors
    AsyncPaginator: Async variant of Paginator
    AsyncPage: Async variant of Page

Example:
    ```python
    from faststack.core.pagination import Paginator

    items = list(range(100))
    paginator = Paginator(items, per_page=10)

    # Get page safely (handles invalid numbers)
    page = paginator.get_page(1)

    # Iterate over items
    for item in page:
        print(item)

    # Navigation
    if page.has_next():
        next_page = paginator.page(page.next_page_number())
    ```

Async Example:
    ```python
    from faststack.core.pagination import AsyncPaginator

    async def get_paginated_results():
        paginator = AsyncPaginator(items, per_page=10)
        page = await paginator.aget_page(1)

        async for item in page:
            print(item)
    ```
"""

from faststack.core.pagination.paginator import (
    AsyncPage,
    AsyncPaginator,
    EmptyPage,
    InvalidPage,
    Page,
    PageLike,
    PageNotAnInteger,
    Paginator,
    PaginatorLike,
)

__all__ = [
    # Core classes
    "Paginator",
    "Page",
    "EmptyPage",
    "PageNotAnInteger",
    "InvalidPage",
    # Async variants
    "AsyncPaginator",
    "AsyncPage",
    # Type aliases
    "PageLike",
    "PaginatorLike",
]
