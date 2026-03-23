---
Task ID: 1
Agent: general-purpose
Task: Build Pagination System

Work Log:
- Created directory `/home/z/my-project/faststack/core/pagination/`
- Created file `/home/z/my-project/faststack/core/pagination/paginator.py` with:
  - EmptyPage exception class (with page_number attribute)
  - PageNotAnInteger exception class (with value attribute)
  - InvalidPage base exception class
  - Page class with full navigation support and iteration
  - Paginator class with orphan handling and lazy count support
  - AsyncPage class with async iteration (`__aiter__`)
  - AsyncPaginator class with fully async page retrieval
- Created file `/home/z/my-project/faststack/core/pagination/__init__.py` with:
  - All class exports
  - Type aliases (PageLike, PaginatorLike)
  - Comprehensive docstrings with usage examples

Stage Summary:
- Implemented complete pagination system with Django-compatible API
- Added async-first support via AsyncPaginator and AsyncPage classes
- Included orphan handling for better UX on last page
- Support for lazy object lists with count() and acount() methods
- Graceful page handling via get_page() / aget_page() methods
- Strict page handling via page() / apage() methods with exceptions
- Full type hints and comprehensive docstrings throughout
