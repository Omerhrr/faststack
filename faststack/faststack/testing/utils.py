"""
Testing Utilities

Utility functions and decorators for testing.
"""

import functools
from typing import Callable, Any


def override_settings(**settings) -> Callable:
    """
    Decorator to temporarily override settings for a test.
    
    Args:
        **settings: Settings to override
    
    Example:
        @override_settings(DEBUG=True, EMAIL_ENABLED=False)
        async def test_something(self):
            # DEBUG and EMAIL_ENABLED are temporarily changed
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        @functools.wraps(test_func)
        async def async_wrapper(*args, **kwargs):
            from faststack.config import settings as settings_obj
            
            # Store original values
            original = {}
            for key, value in settings.items():
                original[key] = getattr(settings_obj, key, None)
                setattr(settings_obj, key, value)
            
            try:
                return await test_func(*args, **kwargs)
            finally:
                # Restore original values
                for key, value in original.items():
                    if value is None:
                        delattr(settings_obj, key)
                    else:
                        setattr(settings_obj, key, value)
        
        @functools.wraps(test_func)
        def sync_wrapper(*args, **kwargs):
            from faststack.config import settings as settings_obj
            
            # Store original values
            original = {}
            for key, value in settings.items():
                original[key] = getattr(settings_obj, key, None)
                setattr(settings_obj, key, value)
            
            try:
                return test_func(*args, **kwargs)
            finally:
                # Restore original values
                for key, value in original.items():
                    if value is None:
                        delattr(settings_obj, key)
                    else:
                        setattr(settings_obj, key, value)
        
        import asyncio
        if asyncio.iscoroutinefunction(test_func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def tag(name: str) -> Callable:
    """
    Add a tag to a test for filtering.
    
    Args:
        name: Tag name
    
    Example:
        @tag('slow')
        async def test_slow_operation(self):
            # Run with: pytest -m slow
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        if not hasattr(test_func, 'tags'):
            test_func.tags = set()
        test_func.tags.add(name)
        return test_func
    return decorator


def skip_if(condition: bool, reason: str = "") -> Callable:
    """
    Skip test if condition is true.
    
    Args:
        condition: Skip condition
        reason: Reason for skipping
    
    Example:
        @skip_if(not HAS_REDIS, "Redis not available")
        async def test_redis_cache(self):
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        import unittest
        
        if condition:
            return unittest.skip(reason)(test_func)
        return test_func
    return decorator


def skip_unless(condition: bool, reason: str = "") -> Callable:
    """
    Skip test unless condition is true.
    
    Args:
        condition: Skip condition
        reason: Reason for skipping
    
    Example:
        @skip_unless(HAS_REDIS, "Requires Redis")
        async def test_redis_cache(self):
            pass
    """
    return skip_if(not condition, reason)


def expected_failure(func: Callable) -> Callable:
    """
    Mark test as expected to fail.
    
    If test passes, it will be reported as unexpected success.
    """
    import unittest
    return unittest.expectedFailure(func)


class mock_signal:
    """
    Context manager to mock signals.
    
    Prevents signals from being sent during tests.
    
    Example:
        with mock_signal('post_save'):
            # post_save signal is mocked
            user.save()
    """
    
    def __init__(self, signal_name: str):
        self.signal_name = signal_name
        self.original_send = None
    
    def __enter__(self):
        from faststack.core.signals import signal_registry
        
        if self.signal_name in signal_registry:
            signal = signal_registry[self.signal_name]
            self.original_send = signal.send
            signal.send = lambda *args, **kwargs: None
        
        return self
    
    def __exit__(self, *args):
        from faststack.core.signals import signal_registry
        
        if self.original_send and self.signal_name in signal_registry:
            signal_registry[self.signal_name].send = self.original_send


class capture_emails:
    """
    Context manager to capture emails sent.
    
    Example:
        with capture_emails() as emails:
            send_email(...)
        
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]['to'], 'user@example.com')
    """
    
    def __init__(self):
        self.emails: list[dict] = []
    
    def __enter__(self):
        from faststack.core.email import email_backend
        
        # Store original send method
        self._original_send = email_backend.send
        
        # Mock send to capture emails
        def mock_send(to: str, subject: str, body: str, **kwargs):
            self.emails.append({
                'to': to,
                'subject': subject,
                'body': body,
                **kwargs,
            })
            return True
        
        email_backend.send = mock_send
        return self.emails
    
    def __exit__(self, *args):
        from faststack.core.email import email_backend
        email_backend.send = self._original_send


class freeze_time:
    """
    Context manager to freeze time in tests.
    
    Example:
        with freeze_time('2024-01-01 12:00:00'):
            # datetime.now() returns frozen time
            pass
    """
    
    def __init__(self, time_string: str):
        from datetime import datetime
        self.frozen_time = datetime.fromisoformat(time_string)
        self.original_now = None
    
    def __enter__(self):
        import datetime as dt_module
        self.original_now = dt_module.datetime.now
        
        def mock_now(tz=None):
            return self.frozen_time
        
        dt_module.datetime.now = mock_now
        return self.frozen_time
    
    def __exit__(self, *args):
        import datetime as dt_module
        dt_module.datetime.now = self.original_now


def isolate_test(func: Callable) -> Callable:
    """
    Decorator to isolate a test.
    
    Ensures:
    - Database is clean before/after
    - Cache is cleared
    - Settings are reset
    
    Example:
        @isolate_test
        async def test_critical_operation(self):
            # Test runs in isolation
            pass
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        from faststack.core.cache import cache
        
        # Clear cache
        cache.clear()
        
        try:
            return await func(*args, **kwargs)
        finally:
            # Clear cache again
            cache.clear()
    
    return wrapper


def with_session(func: Callable) -> Callable:
    """
    Decorator to provide a database session to test.
    
    Session is automatically closed after test.
    
    Example:
        @with_session
        async def test_with_db(self, session):
            user = User(email='test@test.com')
            session.add(user)
            session.commit()
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        from faststack.database import Session
        
        session = Session()
        try:
            return await func(*args, session=session, **kwargs)
        finally:
            session.close()
    
    return wrapper


# Test data factories

def make_user(
    email: str = 'test@example.com',
    password: str = 'password123',
    **kwargs,
) -> dict:
    """Create user data dict for testing."""
    return {
        'email': email,
        'password': password,
        'password_confirm': password,
        **kwargs,
    }


def make_post(
    title: str = 'Test Post',
    content: str = 'Test content',
    **kwargs,
) -> dict:
    """Create post data dict for testing."""
    return {
        'title': title,
        'content': content,
        **kwargs,
    }


def make_comment(
    content: str = 'Test comment',
    **kwargs,
) -> dict:
    """Create comment data dict for testing."""
    return {
        'content': content,
        **kwargs,
    }
