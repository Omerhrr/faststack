"""
Session model for database-backed sessions.
"""

from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Session:
    """
    Session model for database storage.

    Attributes:
        session_key: Unique session identifier
        session_data: Encoded session data
        expire_date: When the session expires
    """

    session_key: str
    session_data: str
    expire_date: datetime

    # Table name for ORM
    __tablename__ = 'sessions'

    @classmethod
    async def create_table(cls, db):
        """Create sessions table."""
        query = """
        CREATE TABLE IF NOT EXISTS sessions (
            session_key VARCHAR(40) PRIMARY KEY,
            session_data TEXT NOT NULL,
            expire_date TIMESTAMP NOT NULL,
            INDEX idx_expire_date (expire_date)
        )
        """
        await db.execute(query)

    @classmethod
    async def get(cls, session_key: str, db=None) -> Optional['Session']:
        """Get a session by key."""
        if db is None:
            return None

        query = "SELECT * FROM sessions WHERE session_key = ?"
        row = await db.fetch_one(query, [session_key])

        if row:
            return cls(
                session_key=row['session_key'],
                session_data=row['session_data'],
                expire_date=row['expire_date']
            )
        return None

    @classmethod
    async def exists(cls, session_key: str, db=None) -> bool:
        """Check if session exists."""
        if db is None:
            return False

        query = "SELECT 1 FROM sessions WHERE session_key = ?"
        row = await db.fetch_one(query, [session_key])
        return row is not None

    async def save(self, db=None) -> None:
        """Save the session."""
        if db is None:
            return

        query = """
        INSERT INTO sessions (session_key, session_data, expire_date)
        VALUES (?, ?, ?)
        ON CONFLICT (session_key) DO UPDATE SET
            session_data = EXCLUDED.session_data,
            expire_date = EXCLUDED.expire_date
        """
        await db.execute(query, [self.session_key, self.session_data, self.expire_date])

    async def delete(self, db=None) -> None:
        """Delete the session."""
        if db is None:
            return

        query = "DELETE FROM sessions WHERE session_key = ?"
        await db.execute(query, [self.session_key])

    @classmethod
    async def clear_expired(cls, db=None) -> int:
        """Clear all expired sessions."""
        if db is None:
            return 0

        query = "DELETE FROM sessions WHERE expire_date < ?"
        result = await db.execute(query, [datetime.utcnow()])
        return result.rowcount
