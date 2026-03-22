"""
FastStack Response Utilities

Provides custom response classes and helpers for HTMX and web responses.
"""

from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.datastructures import Headers


class HTMXResponse:
    """
    HTMX-specific response utilities.

    Provides methods for creating HTMX-compatible responses with
    appropriate headers for client-side navigation and updates.
    """

    @staticmethod
    def trigger(
        content: str,
        event: str,
        params: dict[str, Any] | None = None,
        status_code: int = 200,
    ) -> HTMLResponse:
        """
        Create a response that triggers an HTMX event.

        Args:
            content: HTML content
            event: Event name to trigger
            params: Event parameters
            status_code: HTTP status code

        Returns:
            HTMLResponse with trigger headers
        """
        headers = {"HX-Trigger": event}
        if params:
            import json
            headers["HX-Trigger"] = json.dumps({event: params})

        return HTMLResponse(
            content=content,
            status_code=status_code,
            headers=headers,
        )

    @staticmethod
    def redirect(
        url: str,
    ) -> HTMLResponse:
        """
        Create an HTMX redirect response.

        Args:
            url: URL to redirect to

        Returns:
            HTMLResponse with redirect header
        """
        return HTMLResponse(
            content="",
            status_code=200,
            headers={"HX-Redirect": url},
        )

    @staticmethod
    def refresh() -> HTMLResponse:
        """
        Create an HTMX refresh response.

        Returns:
            HTMLResponse with refresh header
        """
        return HTMLResponse(
            content="",
            status_code=200,
            headers={"HX-Refresh": "true"},
        )

    @staticmethod
    def retarget(
        content: str,
        target: str,
    ) -> HTMLResponse:
        """
        Create a response that retargets HTMX.

        Args:
            content: HTML content
            target: New CSS selector target

        Returns:
            HTMLResponse with retarget header
        """
        return HTMLResponse(
            content=content,
            status_code=200,
            headers={"HX-Retarget": target},
        )

    @staticmethod
    def push_url(
        content: str,
        url: str,
    ) -> HTMLResponse:
        """
        Create a response that pushes a URL to browser history.

        Args:
            content: HTML content
            url: URL to push

        Returns:
            HTMLResponse with push URL header
        """
        return HTMLResponse(
            content=content,
            status_code=200,
            headers={"HX-Push-Url": url},
        )

    @staticmethod
    def swap(
        content: str,
        swap: str = "innerHTML",
    ) -> HTMLResponse:
        """
        Create a response with custom swap behavior.

        Args:
            content: HTML content
            swap: Swap behavior (innerHTML, outerHTML, beforeend, etc.)

        Returns:
            HTMLResponse with swap header
        """
        return HTMLResponse(
            content=content,
            status_code=200,
            headers={"HX-Reswap": swap},
        )


def redirect(
    url: str,
    status_code: int = 302,
) -> RedirectResponse:
    """
    Create a redirect response.

    Args:
        url: URL to redirect to
        status_code: HTTP status code (default: 302)

    Returns:
        RedirectResponse
    """
    return RedirectResponse(url=url, status_code=status_code)


def is_htmx(request: Request) -> bool:
    """
    Check if the request is from HTMX.

    Args:
        request: FastAPI request

    Returns:
        True if request is from HTMX
    """
    return request.headers.get("HX-Request", "false").lower() == "true"


def get_htmx_target(request: Request) -> str | None:
    """
    Get the HTMX target element.

    Args:
        request: FastAPI request

    Returns:
        Target CSS selector or None
    """
    return request.headers.get("HX-Target")


def get_htmx_trigger(request: Request) -> str | None:
    """
    Get the HTMX trigger element ID.

    Args:
        request: FastAPI request

    Returns:
        Trigger element ID or None
    """
    return request.headers.get("HX-Trigger")


def get_htmx_prompt(request: Request) -> str | None:
    """
    Get the HTMX prompt response.

    Args:
        request: FastAPI request

    Returns:
        Prompt response or None
    """
    return request.headers.get("HX-Prompt")
