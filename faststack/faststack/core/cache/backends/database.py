"""
Database Cache Backend

Uses a database table for cache storage.
"""

import time
import json
from typing import Any

from faststack.faststack.core.cache.base import BaseCache


class DatabaseCache(BaseCache):
    """
    Database-backed cache.
    
    Uses SQLModel/SQLAlchemy to store cache entries in a database table.
    Useful when Redis is not available but you need persistent caching.
    
    Example:
        cache = DatabaseCache(
            table_name="cache_entries",
            timeout=300,
        )
    """
    
    def __init__(
        self,
        table_name: str = "cache_entries",
        timeout: int = 300,
        key_prefix: str = "",
        version: int = 1,
        session_factory: Any = None,
        **kwargs,
    ):
        """
        Initialize database cache.
        
        Args:
            table_name: Database table name
            timeout: Default timeout in seconds
            key_prefix: Prefix for all cache keys
            version: Cache version
            session_factory: Database session factory
        """
        super().__init__(timeout, key_prefix, version, **kwargs)
        self.table_name = table_name
        self.session_factory = session_factory
        self._model = None
    
    def _get_model(self):
        """Get or create the cache entry model."""
        if self._model is None:
            from sqlmodel import Field, SQLModel, Session
            from datetime import datetime
            
            # Create a dynamic model class
            class CacheEntry(SQLModel, table=True):
                __tablename__ = self.table_name
                
                key: str = Field(primary_key=True)
                value: str
                expires_at: float  # Unix timestamp
                
                class Config:
                    table_name = self.table_name
            
            self._model = CacheEntry
        
        return self._model
    
    def _get_session(self):
        """Get a database session."""
        if self.session_factory:
            return self.session_factory()
        
        from faststack.database import Session
        return Session()
    
    def _encode(self, value: Any) -> str:
        """Encode a value for storage."""
        return json.dumps(value, default=str)
    
    def _decode(self, value: str | None) -> Any:
        """Decode a value from storage."""
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    def add(self, key: str, value: Any, timeout: int | None = None) -> bool:
        """Add a value if key doesn't exist."""
        Model = self._get_model()
        full_key = self.make_key(key)
        timeout = self.get_timeout(timeout)
        expires_at = time.time() + timeout
        
        with self._get_session() as session:
            # Check if exists
            existing = session.get(Model, full_key)
            if existing is not None and existing.expires_at > time.time():
                return False
            
            # Set value
            entry = Model(
                key=full_key,
                value=self._encode(value),
                expires_at=expires_at,
            )
            session.add(entry)
            session.commit()
            return True
    
    def get(self, key: str, default: Any = None, version: int | None = None) -> Any:
        """Get a value from the cache."""
        Model = self._get_model()
        full_key = self.make_key(key, version)
        
        with self._get_session() as session:
            entry = session.get(Model, full_key)
            
            if entry is None:
                return default
            
            # Check expiry
            if entry.expires_at < time.time():
                session.delete(entry)
                session.commit()
                return default
            
            return self._decode(entry.value)
    
    def set(self, key: str, value: Any, timeout: int | None = None) -> None:
        """Set a value in the cache."""
        Model = self._get_model()
        full_key = self.make_key(key)
        timeout = self.get_timeout(timeout)
        expires_at = time.time() + timeout
        
        with self._get_session() as session:
            entry = session.get(Model, full_key)
            
            if entry is None:
                entry = Model(
                    key=full_key,
                    value=self._encode(value),
                    expires_at=expires_at,
                )
                session.add(entry)
            else:
                entry.value = self._encode(value)
                entry.expires_at = expires_at
            
            session.commit()
    
    def delete(self, key: str, version: int | None = None) -> bool:
        """Delete a key from the cache."""
        Model = self._get_model()
        full_key = self.make_key(key, version)
        
        with self._get_session() as session:
            entry = session.get(Model, full_key)
            if entry is not None:
                session.delete(entry)
                session.commit()
                return True
            return False
    
    def exists(self, key: str, version: int | None = None) -> bool:
        """Check if a key exists."""
        Model = self._get_model()
        full_key = self.make_key(key, version)
        
        with self._get_session() as session:
            entry = session.get(Model, full_key)
            if entry is None:
                return False
            
            if entry.expires_at < time.time():
                session.delete(entry)
                session.commit()
                return False
            
            return True
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        Model = self._get_model()
        
        with self._get_session() as session:
            from sqlmodel import delete
            session.exec(delete(Model))
            session.commit()
    
    def cull_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        Model = self._get_model()
        now = time.time()
        
        with self._get_session() as session:
            from sqlmodel import select, delete
            
            statement = delete(Model).where(Model.expires_at < now)
            result = session.exec(statement)
            session.commit()
            return result.rowcount if hasattr(result, 'rowcount') else 0
