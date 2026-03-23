"""
FastStack Test Configuration

Provides fixtures and configuration for testing FastStack applications.
"""

import os
import sys
import asyncio
from typing import Generator, AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import Session, SQLModel
from sqlalchemy.ext.asyncio import AsyncSession

# Configure test environment BEFORE any imports
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///./test_faststack.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32chars"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-32chars"

# Add faststack to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    from sqlmodel import create_engine
    
    # Use a fresh in-memory database for each test
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Create all tables
    SQLModel.metadata.create_all(engine)
    
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        SQLModel.metadata.drop_all(engine)


@pytest_asyncio.fixture(scope="function")
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh async database session for each test."""
    from sqlalchemy.ext.asyncio import create_async_engine
    
    # Use a fresh in-memory database for each test
    async_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create all tables
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    async with AsyncSession(async_engine) as session:
        try:
            yield session
        finally:
            await session.close()
    
    # Drop all tables after test
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture(scope="function")
def test_app():
    """Create a test FastAPI application."""
    from faststack.app import create_app
    
    app = create_app(
        title="Test App",
        version="0.0.1",
        enable_session=True,
        enable_csrf=False,  # Disable CSRF for easier testing
        enable_rate_limit=False,  # Disable rate limiting for tests
        enable_security_headers=False,
    )
    
    return app


@pytest_asyncio.fixture(scope="function")
async def client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def test_admin_data():
    """Sample admin user data for testing."""
    return {
        "email": "admin@example.com",
        "password": "AdminPassword123",
        "first_name": "Admin",
        "last_name": "User",
        "is_admin": True,
    }


@pytest.fixture
def create_test_user(db_session):
    """Factory fixture to create test users."""
    from faststack.auth.utils import hash_password
    from faststack.auth.models import User
    
    def _create_user(
        email: str = "test@example.com",
        password: str = "TestPassword123",
        is_admin: bool = False,
        is_active: bool = True,
        **kwargs
    ) -> User:
        user = User(
            email=email,
            password_hash=hash_password(password),
            is_admin=is_admin,
            is_active=is_active,
            **kwargs
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    return _create_user
