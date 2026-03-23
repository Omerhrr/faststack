"""
Test Case Classes

Base test classes for FastStack testing.
"""

import asyncio
import unittest
from typing import Any
from contextlib import asynccontextmanager

from faststack.testing.client import AsyncClient, Response


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    """
    Async test case with FastStack helpers.
    
    Provides:
    - Async test client
    - Database setup/teardown
    - Fixture loading
    - Assertion helpers
    
    Example:
        class UserTests(AsyncTestCase):
            fixtures = ['users.json']
            
            async def test_user_list(self):
                async with AsyncClient() as client:
                    response = await client.get('/api/users/')
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'test@example.com')
    """
    
    # Fixtures to load before each test
    fixtures: list[str] = []
    
    # Whether to use transactions for test isolation
    use_transactions = True
    
    # Database session
    _session: Any = None
    
    async def asyncSetUp(self) -> None:
        """Set up test environment."""
        await super().asyncSetUp()
        
        # Load fixtures
        if self.fixtures:
            from faststack.testing.fixtures import load_fixtures
            await load_fixtures(self.fixtures, self._get_session())
    
    async def asyncTearDown(self) -> None:
        """Tear down test environment."""
        # Close session
        if self._session:
            self._session.close()
            self._session = None
        
        await super().asyncTearDown()
    
    def _get_session(self) -> Any:
        """Get database session."""
        if self._session is None:
            from faststack.database import Session
            self._session = Session()
        return self._session
    
    @asynccontextmanager
    async def client(self, **kwargs):
        """
        Context manager for test client.
        
        Example:
            async with self.client() as client:
                response = await client.get('/')
        """
        async with AsyncClient(**kwargs) as client:
            yield client
    
    # Assertion helpers
    
    def assertResponseOK(self, response: Response) -> None:
        """Assert response status is 2xx."""
        self.assertTrue(
            200 <= response.status_code < 300,
            f"Expected successful response, got {response.status_code}"
        )
    
    def assertStatusCode(self, response: Response, status_code: int) -> None:
        """Assert response status code."""
        self.assertEqual(
            response.status_code,
            status_code,
            f"Expected status {status_code}, got {response.status_code}"
        )
    
    def assertContains(self, response: Response, text: str, count: int | None = None) -> None:
        """Assert response contains text."""
        content = response.text
        actual_count = content.count(text)
        
        if count is not None:
            self.assertEqual(
                actual_count,
                count,
                f"Expected '{text}' to appear {count} times, found {actual_count}"
            )
        else:
            self.assertIn(
                text,
                content,
                f"Expected response to contain '{text}'"
            )
    
    def assertNotContains(self, response: Response, text: str) -> None:
        """Assert response does not contain text."""
        self.assertNotIn(
            text,
            response.text,
            f"Response should not contain '{text}'"
        )
    
    def assertRedirects(
        self,
        response: Response,
        expected_url: str,
        status_code: int = 302,
    ) -> None:
        """Assert response redirects to expected URL."""
        self.assertEqual(
            response.status_code,
            status_code,
            f"Expected status {status_code}, got {response.status_code}"
        )
        
        actual_url = response.headers.get('Location', '')
        self.assertEqual(
            actual_url,
            expected_url,
            f"Expected redirect to '{expected_url}', got '{actual_url}'"
        )
    
    def assertJSONEqual(self, response: Response, expected: dict) -> None:
        """Assert JSON response equals expected."""
        actual = response.json
        self.assertEqual(actual, expected)
    
    def assertJSONContains(self, response: Response, key: str, value: Any = None) -> None:
        """Assert JSON response contains key with optional value."""
        data = response.json
        
        self.assertIn(
            key,
            data,
            f"JSON response missing key '{key}'"
        )
        
        if value is not None:
            self.assertEqual(
                data[key],
                value,
                f"Expected {key}={value!r}, got {data[key]!r}"
            )
    
    def assertFormError(self, response: Response, form_name: str, field: str, error: str) -> None:
        """Assert form has specific error."""
        from faststack.testing.assertions import assert_form_error
        assert_form_error(response, form_name, field, error)
    
    def assertTemplateUsed(self, response: Response, template_name: str) -> None:
        """Assert specific template was used."""
        # This requires template context to be available
        templates = getattr(response, 'templates', [])
        template_names = [t.name for t in templates] if templates else []
        
        self.assertIn(
            template_name,
            template_names,
            f"Expected template '{template_name}' to be used"
        )
    
    async def assertQueryCount(self, expected_count: int) -> None:
        """Assert number of database queries (requires query tracking)."""
        # This requires query tracking middleware
        pass


class SyncTestCase(unittest.TestCase):
    """
    Synchronous test case for simple tests.
    
    Use AsyncTestCase for most cases; this is provided for
    testing sync code or simpler test scenarios.
    """
    
    fixtures: list[str] = []
    
    def setUp(self) -> None:
        """Set up test environment."""
        super().setUp()
        
        # Load fixtures
        if self.fixtures:
            from faststack.testing.fixtures import load_fixtures
            # Run async fixture loading in sync context
            asyncio.get_event_loop().run_until_complete(
                load_fixtures(self.fixtures)
            )
    
    def tearDown(self) -> None:
        """Tear down test environment."""
        super().tearDown()


class TransactionTestCase(AsyncTestCase):
    """
    Test case with transaction rollback.
    
    Each test runs in a transaction that is rolled back after,
    providing test isolation without rebuilding the database.
    """
    
    use_transactions = True
    
    async def asyncSetUp(self) -> None:
        """Set up test with transaction."""
        await super().asyncSetUp()
        
        # Begin transaction
        session = self._get_session()
        self._transaction = session.begin_nested()
    
    async def asyncTearDown(self) -> None:
        """Roll back transaction."""
        # Rollback transaction
        if hasattr(self, '_transaction'):
            self._transaction.rollback()
        
        await super().asyncTearDown()


class APITestCase(AsyncTestCase):
    """
    Test case for API testing.
    
    Includes helpers for:
    - JSON request/response handling
    - Authentication
    - Pagination
    """
    
    async def api_get(self, path: str, **kwargs) -> Response:
        """Make an API GET request."""
        async with AsyncClient() as client:
            kwargs.setdefault('headers', {})['Accept'] = 'application/json'
            return await client.get(path, **kwargs)
    
    async def api_post(self, path: str, data: dict | None = None, **kwargs) -> Response:
        """Make an API POST request."""
        async with AsyncClient() as client:
            kwargs.setdefault('headers', {})['Content-Type'] = 'application/json'
            kwargs.setdefault('headers', {})['Accept'] = 'application/json'
            return await client.post(path, json=data, **kwargs)
    
    async def api_put(self, path: str, data: dict | None = None, **kwargs) -> Response:
        """Make an API PUT request."""
        async with AsyncClient() as client:
            kwargs.setdefault('headers', {})['Content-Type'] = 'application/json'
            kwargs.setdefault('headers', {})['Accept'] = 'application/json'
            return await client.put(path, json=data, **kwargs)
    
    async def api_patch(self, path: str, data: dict | None = None, **kwargs) -> Response:
        """Make an API PATCH request."""
        async with AsyncClient() as client:
            kwargs.setdefault('headers', {})['Content-Type'] = 'application/json'
            kwargs.setdefault('headers', {})['Accept'] = 'application/json'
            return await client.patch(path, json=data, **kwargs)
    
    async def api_delete(self, path: str, **kwargs) -> Response:
        """Make an API DELETE request."""
        async with AsyncClient() as client:
            kwargs.setdefault('headers', {})['Accept'] = 'application/json'
            return await client.delete(path, **kwargs)
    
    async def authenticate(self, user: Any) -> AsyncClient:
        """
        Get an authenticated client.
        
        Args:
            user: User to authenticate as
        
        Returns:
            Authenticated client
        """
        client = AsyncClient()
        client.login(user)
        return client
    
    def assertPaginatedResponse(
        self,
        response: Response,
        expected_count: int | None = None,
    ) -> dict:
        """
        Assert response is paginated correctly.
        
        Returns:
            The results list
        """
        data = response.json
        
        self.assertIn('results', data)
        self.assertIn('count', data)
        
        if expected_count is not None:
            self.assertEqual(data['count'], expected_count)
        
        return data['results']
