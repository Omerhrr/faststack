"""
FastStack Testing Utilities

Provides Django-like testing utilities for FastStack applications.

Features:
- AsyncTestCase base class
- Test client for making requests
- Fixture loading
- Database fixtures and transactions
- Assertion helpers
- Mock utilities

Example:
    from faststack.testing import AsyncTestCase, Client
    
    class MyTestCase(AsyncTestCase):
        fixtures = ['users.json']
        
        async def test_login(self):
            async with Client() as client:
                response = await client.post('/login/', data={
                    'email': 'user@example.com',
                    'password': 'password',
                })
                self.assertEqual(response.status_code, 302)
"""

from faststack.testing.testcases import (
    AsyncTestCase,
    SyncTestCase,
    TransactionTestCase,
)
from faststack.testing.client import Client, AsyncClient
from faststack.testing.fixtures import (
    load_fixture,
    load_fixtures,
    create_fixture,
)
from faststack.testing.assertions import (
    assert_response_status,
    assert_redirects,
    assert_template_used,
    assert_contains,
)
from faststack.testing.utils import (
    override_settings,
    tag,
    skip_if,
)

__all__ = [
    # Test Cases
    "AsyncTestCase",
    "SyncTestCase",
    "TransactionTestCase",
    # Clients
    "Client",
    "AsyncClient",
    # Fixtures
    "load_fixture",
    "load_fixtures",
    "create_fixture",
    # Assertions
    "assert_response_status",
    "assert_redirects",
    "assert_template_used",
    "assert_contains",
    # Utils
    "override_settings",
    "tag",
    "skip_if",
]
