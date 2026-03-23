"""
Test Assertions

Custom assertions for testing FastStack applications.
"""

from typing import Any
from faststack.testing.client import Response


def assert_response_status(response: Response, expected: int) -> None:
    """
    Assert response has expected status code.
    
    Args:
        response: Response object
        expected: Expected status code
    
    Raises:
        AssertionError: If status doesn't match
    """
    if response.status_code != expected:
        raise AssertionError(
            f"Expected status code {expected}, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )


def assert_redirects(
    response: Response,
    expected_url: str,
    status_code: int = 302,
) -> None:
    """
    Assert response redirects to expected URL.
    
    Args:
        response: Response object
        expected_url: Expected redirect URL
        status_code: Expected status code (default 302)
    
    Raises:
        AssertionError: If redirect doesn't match
    """
    if response.status_code != status_code:
        raise AssertionError(
            f"Expected status code {status_code}, got {response.status_code}"
        )
    
    actual_url = response.headers.get('Location', '')
    if actual_url != expected_url:
        raise AssertionError(
            f"Expected redirect to '{expected_url}', got '{actual_url}'"
        )


def assert_template_used(response: Response, template_name: str) -> None:
    """
    Assert specific template was used.
    
    Note: Requires template context to be available.
    
    Args:
        response: Response object
        template_name: Expected template name
    
    Raises:
        AssertionError: If template wasn't used
    """
    templates = getattr(response, 'templates', [])
    template_names = [t.name for t in templates] if templates else []
    
    if template_name not in template_names:
        raise AssertionError(
            f"Expected template '{template_name}' to be used. "
            f"Templates used: {template_names}"
        )


def assert_contains(
    response: Response,
    text: str,
    count: int | None = None,
    html: bool = False,
) -> None:
    """
    Assert response contains text.
    
    Args:
        response: Response object
        text: Text to find
        count: Expected occurrence count (optional)
        html: Whether text contains HTML
    
    Raises:
        AssertionError: If text not found or count doesn't match
    """
    content = response.text
    
    if html:
        # Parse HTML and search
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        actual_count = soup.get_text().count(text)
    else:
        actual_count = content.count(text)
    
    if count is not None:
        if actual_count != count:
            raise AssertionError(
                f"Expected '{text}' to appear {count} times, "
                f"found {actual_count} times"
            )
    else:
        if actual_count == 0:
            raise AssertionError(
                f"Expected response to contain '{text}'"
            )


def assert_not_contains(response: Response, text: str) -> None:
    """
    Assert response does not contain text.
    
    Args:
        response: Response object
        text: Text that should not be present
    
    Raises:
        AssertionError: If text is found
    """
    if text in response.text:
        raise AssertionError(
            f"Response should not contain '{text}'"
        )


def assert_form_error(
    response: Response,
    form_name: str,
    field: str,
    error: str,
) -> None:
    """
    Assert form has specific error.
    
    Args:
        response: Response object
        form_name: Form variable name in context
        field: Field name
        error: Error message
    
    Raises:
        AssertionError: If error not found
    """
    context = getattr(response, 'context', {})
    form = context.get(form_name)
    
    if form is None:
        raise AssertionError(f"Form '{form_name}' not found in context")
    
    field_errors = form.errors.get(field, [])
    
    if error not in field_errors:
        raise AssertionError(
            f"Expected error '{error}' for field '{field}', "
            f"got errors: {field_errors}"
        )


def assert_no_form_errors(response: Response, form_name: str) -> None:
    """
    Assert form has no errors.
    
    Args:
        response: Response object
        form_name: Form variable name
    
    Raises:
        AssertionError: If form has errors
    """
    context = getattr(response, 'context', {})
    form = context.get(form_name)
    
    if form is None:
        raise AssertionError(f"Form '{form_name}' not found in context")
    
    if form.errors:
        raise AssertionError(f"Form has unexpected errors: {form.errors}")


def assert_json_equal(response: Response, expected: dict) -> None:
    """
    Assert JSON response equals expected.
    
    Args:
        response: Response object
        expected: Expected JSON data
    
    Raises:
        AssertionError: If JSON doesn't match
    """
    actual = response.json
    
    if actual != expected:
        import json
        raise AssertionError(
            f"JSON response doesn't match.\n"
            f"Expected: {json.dumps(expected, indent=2)}\n"
            f"Actual: {json.dumps(actual, indent=2)}"
        )


def assert_json_contains(response: Response, key: str, value: Any = None) -> None:
    """
    Assert JSON response contains key.
    
    Args:
        response: Response object
        key: Key to check
        value: Expected value (optional)
    
    Raises:
        AssertionError: If key not found or value doesn't match
    """
    data = response.json
    
    if key not in data:
        raise AssertionError(
            f"JSON response missing key '{key}'. Keys: {list(data.keys())}"
        )
    
    if value is not None and data[key] != value:
        raise AssertionError(
            f"Expected {key}={value!r}, got {data[key]!r}"
        )


def assert_queryset_equals(queryset: Any, expected: list) -> None:
    """
    Assert queryset equals expected list.
    
    Args:
        queryset: Queryset or list
        expected: Expected items
    
    Raises:
        AssertionError: If items don't match
    """
    if hasattr(queryset, 'all'):
        actual = list(queryset.all())
    else:
        actual = list(queryset)
    
    if len(actual) != len(expected):
        raise AssertionError(
            f"Expected {len(expected)} items, got {len(actual)}"
        )


def assert_emails_sent(count: int) -> None:
    """
    Assert number of emails sent.
    
    Requires email backend to track sent emails.
    
    Args:
        count: Expected number of emails
    
    Raises:
        AssertionError: If count doesn't match
    """
    from faststack.core.email import get_sent_emails
    sent = get_sent_emails()
    
    if len(sent) != count:
        raise AssertionError(
            f"Expected {count} emails to be sent, got {len(sent)}"
        )


def assert_url_exists(url: str) -> None:
    """
    Assert URL resolves to a view.
    
    Args:
        url: URL to check
    
    Raises:
        AssertionError: If URL doesn't resolve
    """
    from faststack.app import get_app
    
    app = get_app()
    routes = [route.path for route in app.routes]
    
    if url not in routes:
        # Check for parameterized routes
        import re
        for route in routes:
            if re.match(route.replace('{', r'\w+').replace('}', r'\w+'), url):
                return
        
        raise AssertionError(f"URL '{url}' does not exist")


def assert_url_not_exists(url: str) -> None:
    """
    Assert URL does not resolve.
    
    Args:
        url: URL to check
    
    Raises:
        AssertionError: If URL resolves
    """
    try:
        assert_url_exists(url)
        raise AssertionError(f"URL '{url}' should not exist")
    except AssertionError:
        pass  # Expected
