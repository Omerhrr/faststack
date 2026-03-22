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

from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession, AsyncEngine

from faststack.config import settings


def create_database_engine(async_mode: bool = False) -> AsyncEngine | object:
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
        return AsyncEngine(
            create_engine(
                settings.get_database_url(async_driver=True),
                echo=settings.DATABASE_ECHO,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                connect_args=connect_args,
            )
        )

    return create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        connect_args=connect_args,
    )


# Global engine instances
engine = create_database_engine(async_mode=False)
async_engine: Optional[AsyncEngine] = None


def get_async_engine() -> AsyncEngine:
    """
    Get or create the async database engine.

    Returns:
        AsyncEngine: Async database engine
    """
    global async_engine
    if async_engine is None:
        async_engine = create_database_engine(async_mode=True)
    return async_engine


def get_session() -> Generator[Session, None, None]:
    """
    Dependency injection for synchronous database sessions.

    Yields:
        Session: SQLModel session

    Example:
        @app.get("/items")
        def get_items(session: Session = Depends(get_session)):
            return session.exec(select(Item)).all()
    """
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


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
    with Session(engine) as session:
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
    SQLModel.metadata.create_all(engine)


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
    SQLModel.metadata.drop_all(engine)


async def drop_async_db() -> None:
    """
    Drop all database tables (async version).

    WARNING: This will delete all data! Use only in development/testing.
    """
    async_engine = get_async_engine()
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
