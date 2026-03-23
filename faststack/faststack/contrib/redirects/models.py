"""
Redirect model for URL redirect management.
"""

from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Redirect:
    """
    Model for storing URL redirects.

    Attributes:
        old_path: Original URL path
        new_path: Target URL path
        is_permanent: Use 301 (permanent) vs 302 (temporary)
        site_id: Site this redirect belongs to (for multi-site)
        created_at: When redirect was created

    Example:
        redirect = await Redirect.create(
            old_path='/old-page/',
            new_path='/new-page/',
            is_permanent=True
        )
    """

    id: Optional[int] = None
    old_path: str = ''
    new_path: str = ''
    is_permanent: bool = False
    site_id: Optional[int] = None
    created_at: datetime = None
    hits: int = 0

    # Table name for ORM
    __tablename__ = 'redirects'

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def __repr__(self) -> str:
        perm = '301' if self.is_permanent else '302'
        return f"<Redirect: {self.old_path} -> {self.new_path} ({perm})>"

    def __str__(self) -> str:
        return f"{self.old_path} -> {self.new_path}"

    @classmethod
    async def create_table(cls, db):
        """Create redirects table."""
        query = """
        CREATE TABLE IF NOT EXISTS redirects (
            id SERIAL PRIMARY KEY,
            old_path VARCHAR(255) NOT NULL UNIQUE,
            new_path VARCHAR(255) NOT NULL,
            is_permanent BOOLEAN DEFAULT FALSE,
            site_id INTEGER,
            created_at TIMESTAMP DEFAULT NOW(),
            hits INTEGER DEFAULT 0,
            INDEX idx_old_path (old_path)
        )
        """
        await db.execute(query)

    @classmethod
    async def get(cls, db, old_path: str) -> Optional['Redirect']:
        """Get redirect by old_path."""
        query = "SELECT * FROM redirects WHERE old_path = ?"
        row = await db.fetch_one(query, [old_path])

        if row:
            return cls(
                id=row['id'],
                old_path=row['old_path'],
                new_path=row['new_path'],
                is_permanent=row.get('is_permanent', False),
                site_id=row.get('site_id'),
                created_at=row.get('created_at'),
                hits=row.get('hits', 0)
            )
        return None

    @classmethod
    async def all(cls, db) -> List['Redirect']:
        """Get all redirects."""
        query = "SELECT * FROM redirects ORDER BY old_path"
        rows = await db.fetch_all(query)

        return [
            cls(
                id=row['id'],
                old_path=row['old_path'],
                new_path=row['new_path'],
                is_permanent=row.get('is_permanent', False),
                site_id=row.get('site_id'),
                created_at=row.get('created_at'),
                hits=row.get('hits', 0)
            )
            for row in rows
        ]

    @classmethod
    async def create(cls, db, **kwargs) -> 'Redirect':
        """Create a new redirect."""
        redirect = cls(**kwargs)

        query = """
        INSERT INTO redirects (old_path, new_path, is_permanent, site_id)
        VALUES (?, ?, ?, ?)
        RETURNING id
        """
        result = await db.execute(query, [
            redirect.old_path,
            redirect.new_path,
            redirect.is_permanent,
            redirect.site_id
        ])

        redirect.id = result.lastrowid if hasattr(result, 'lastrowid') else result
        return redirect

    async def save(self, db) -> None:
        """Save redirect changes."""
        query = """
        UPDATE redirects SET
            old_path = ?,
            new_path = ?,
            is_permanent = ?,
            site_id = ?
        WHERE id = ?
        """
        await db.execute(query, [
            self.old_path,
            self.new_path,
            self.is_permanent,
            self.site_id,
            self.id
        ])

    async def delete(self, db) -> None:
        """Delete redirect."""
        query = "DELETE FROM redirects WHERE id = ?"
        await db.execute(query, [self.id])

    async def increment_hits(self, db) -> None:
        """Increment hit counter."""
        self.hits += 1
        query = "UPDATE redirects SET hits = hits + 1 WHERE id = ?"
        await db.execute(query, [self.id])

    @property
    def status_code(self) -> int:
        """Get HTTP status code for redirect."""
        return 301 if self.is_permanent else 302

    def clean(self) -> List[str]:
        """
        Validate redirect data.

        Returns:
            List of error messages
        """
        errors = []

        if not self.old_path:
            errors.append("Old path is required")
        elif not self.old_path.startswith('/'):
            errors.append("Old path must start with a slash")

        if not self.new_path:
            errors.append("New path is required")

        if self.old_path == self.new_path:
            errors.append("Old path and new path cannot be the same")

        return errors
