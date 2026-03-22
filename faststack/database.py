"""
FastStack Database Module

This module provides database engine creation, session management,
and dependency injection helpers for SQLModel.

Usage:
    from faststack.database import get_session, init_db, engine
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Optional
import time

from sqlalchemy.ext.asyncio import AsyncEngine as SQLAlchemyAsyncEngine, create_async_engine
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from faststack.config import settings


def create_database_engine(async_mode: bool = False):
    """
    Create a database engine based on settings.

    Args:
        async_mode: If True, creates an async engine for async operations

    Returns:
        Database engine (sync or async)
    """
    connect_args = {}

    # SQLite specific settings
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    if async_mode:
        return create_async_engine(
            settings.get_database_url(async_driver=True),
            echo=settings.DATABASE_ECHO,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
            connect_args=connect_args,
        )

    return create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
        connect_args=connect_args,
    )


# Global engine instances
_engine = None
_async_engine: Optional[SQLAlchemyAsyncEngine] = None


def get_engine():
    """
    Get or create the sync database engine.

    Returns:
        Engine: Sync database engine
    """
    global _engine
    if _engine is None:
        connect_args = {}
        if settings.DATABASE_URL.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
            connect_args=connect_args,
        )
    return _engine


# Alias for backwards compatibility
engine = get_engine


def get_async_engine() -> SQLAlchemyAsyncEngine:
    """
    Get or create the async database engine.

    Returns:
        SQLAlchemyAsyncEngine: Async database engine
    """
    global _async_engine
    if _async_engine is None:
        connect_args = {}
        if settings.DATABASE_URL.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _async_engine = create_async_engine(
            settings.get_database_url(async_driver=True),
            echo=settings.DATABASE_ECHO,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
            connect_args=connect_args,
        )
    return _async_engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Dependency injection for synchronous database sessions.

    Can be used both as a FastAPI dependency and as a context manager.

    Yields:
        Session: SQLModel session

    Example:
        # As a FastAPI dependency
        @app.get("/items")
        def get_items(session: Session = Depends(get_session)):
            return session.exec(select(Item)).all()

        # As a context manager
        with get_session() as session:
            session.add(Item(name="Test"))
    """
    with Session(get_engine()) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for asynchronous database sessions.

    Yields:
        AsyncSession: Async SQLModel session

    Example:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_async_session)):
            result = await session.exec(select(Item))
            return result.all()
    """
    async_engine = get_async_engine()
    async with AsyncSession(async_engine) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Provides a transactional scope around a series of operations.

    Example:
        with session_scope() as session:
            session.add(Item(name="Test"))
            # Auto-commits on exit
    """
    with Session(get_engine()) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


@asynccontextmanager
async def async_session_scope() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.

    Example:
        async with async_session_scope() as session:
            session.add(Item(name="Test"))
            # Auto-commits on exit
    """
    async_engine = get_async_engine()
    async with AsyncSession(async_engine) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def init_db() -> None:
    """
    Initialize the database by creating all tables.

    This function creates all tables defined in SQLModel subclasses.
    It should be called during application startup.

    Example:
        from faststack.orm.base import BaseModel
        from faststack.auth.models import User

        init_db()  # Creates tables for all models
    """
    SQLModel.metadata.create_all(get_engine())


async def init_async_db() -> None:
    """
    Initialize the async database by creating all tables.

    This is the async version of init_db().
    """
    async_engine = get_async_engine()
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


def drop_db() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data! Use only in development/testing.
    """
    SQLModel.metadata.drop_all(get_engine())


async def drop_async_db() -> None:
    """
    Drop all database tables (async version).

    WARNING: This will delete all data! Use only in development/testing.
    """
    async_engine = get_async_engine()
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


def db_transaction(func):
    """
    Decorator to wrap a function in a database transaction.
    
    Automatically commits on success, rolls back on failure.
    
    Example:
        @db_transaction
        def create_user(email: str):
            with get_session() as session:
                user = User(email=email)
                session.add(user)
                return user
    """
    def wrapper(*args, **kwargs):
        with session_scope() as session:
            return func(*args, session=session, **kwargs)
    return wrapper


def async_db_transaction(func):
    """
    Decorator to wrap an async function in a database transaction.
    
    Example:
        @async_db_transaction
        async def create_user(email: str):
            async with async_session_scope() as session:
                user = User(email=email)
                session.add(user)
                return user
    """
    async def wrapper(*args, **kwargs):
        async with async_session_scope() as session:
            return await func(*args, session=session, **kwargs)
    return wrapper


def retry_on_deadlock(max_retries: int = 3, delay: float = 0.1):
    """
    Decorator to retry database operations on deadlock.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    
    Example:
        @retry_on_deadlock(max_retries=3)
        def update_user(user_id: int):
            with get_session() as session:
                user = session.get(User, user_id)
                user.name = "New Name"
                session.add(user)
    """
    from sqlalchemy.exc import OperationalError
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    if "deadlock" in str(e).lower():
                        last_exception = e
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
                        continue
                    raise
            raise last_exception
        return wrapper
    return decorator
