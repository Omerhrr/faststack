"""
FlatPage model for simple CMS functionality.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import re


@dataclass
class FlatPage:
    """
    A simple flatpage for static content.

    Attributes:
        url: URL path (e.g., '/about/')
        title: Page title
        content: HTML content
        template_name: Custom template (optional)
        registration_required: Require login to view
        sites: Sites this page is available on

    Example:
        page = await FlatPage.create(
            url='/about/',
            title='About Us',
            content='<h1>About Us</h1>'
        )
    """

    id: Optional[int] = None
    url: str = ''
    title: str = ''
    content: str = ''
    template_name: str = ''
    registration_required: bool = False
    sites: List[int] = field(default_factory=list)
    created_at: datetime = None
    updated_at: datetime = None

    # Table name for ORM
    __tablename__ = 'flatpages'

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<FlatPage: {self.url}>"

    def __str__(self) -> str:
        return self.url

    @classmethod
    async def create_table(cls, db):
        """Create flatpages table."""
        query = """
        CREATE TABLE IF NOT EXISTS flatpages (
            id SERIAL PRIMARY KEY,
            url VARCHAR(100) NOT NULL UNIQUE,
            title VARCHAR(200) NOT NULL,
            content TEXT NOT NULL,
            template_name VARCHAR(70),
            registration_required BOOLEAN DEFAULT FALSE,
            sites JSONB DEFAULT '[]',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
        await db.execute(query)

    @classmethod
    async def get(cls, db, url: str) -> Optional['FlatPage']:
        """Get flatpage by URL."""
        query = "SELECT * FROM flatpages WHERE url = ?"
        row = await db.fetch_one(query, [url])

        if row:
            return cls(
                id=row['id'],
                url=row['url'],
                title=row['title'],
                content=row['content'],
                template_name=row.get('template_name', ''),
                registration_required=row.get('registration_required', False),
                sites=row.get('sites', []),
                created_at=row.get('created_at'),
                updated_at=row.get('updated_at')
            )
        return None

    @classmethod
    async def get_by_id(cls, db, id: int) -> Optional['FlatPage']:
        """Get flatpage by ID."""
        query = "SELECT * FROM flatpages WHERE id = ?"
        row = await db.fetch_one(query, [id])

        if row:
            return cls(
                id=row['id'],
                url=row['url'],
                title=row['title'],
                content=row['content'],
                template_name=row.get('template_name', ''),
                registration_required=row.get('registration_required', False),
                sites=row.get('sites', []),
                created_at=row.get('created_at'),
                updated_at=row.get('updated_at')
            )
        return None

    @classmethod
    async def all(cls, db) -> List['FlatPage']:
        """Get all flatpages."""
        query = "SELECT * FROM flatpages ORDER BY url"
        rows = await db.fetch_all(query)

        return [
            cls(
                id=row['id'],
                url=row['url'],
                title=row['title'],
                content=row['content'],
                template_name=row.get('template_name', ''),
                registration_required=row.get('registration_required', False),
                sites=row.get('sites', []),
                created_at=row.get('created_at'),
                updated_at=row.get('updated_at')
            )
            for row in rows
        ]

    @classmethod
    async def create(cls, db, **kwargs) -> 'FlatPage':
        """Create a new flatpage."""
        page = cls(**kwargs)

        query = """
        INSERT INTO flatpages (url, title, content, template_name, registration_required, sites)
        VALUES (?, ?, ?, ?, ?, ?)
        RETURNING id
        """
        result = await db.execute(query, [
            page.url,
            page.title,
            page.content,
            page.template_name,
            page.registration_required,
            page.sites
        ])

        page.id = result.lastrowid if hasattr(result, 'lastrowid') else result
        return page

    async def save(self, db) -> None:
        """Save flatpage changes."""
        self.updated_at = datetime.utcnow()

        query = """
        UPDATE flatpages SET
            url = ?,
            title = ?,
            content = ?,
            template_name = ?,
            registration_required = ?,
            sites = ?,
            updated_at = ?
        WHERE id = ?
        """
        await db.execute(query, [
            self.url,
            self.title,
            self.content,
            self.template_name,
            self.registration_required,
            self.sites,
            self.updated_at,
            self.id
        ])

    async def delete(self, db) -> None:
        """Delete flatpage."""
        query = "DELETE FROM flatpages WHERE id = ?"
        await db.execute(query, [self.id])

    def clean(self) -> List[str]:
        """
        Validate flatpage data.

        Returns:
            List of error messages
        """
        errors = []

        # URL validation
        if not self.url:
            errors.append("URL is required")
        elif not self.url.startswith('/'):
            errors.append("URL must start with a slash")
        elif not self.url.endswith('/'):
            errors.append("URL must end with a slash")

        # Title validation
        if not self.title:
            errors.append("Title is required")

        # Content validation
        if not self.content:
            errors.append("Content is required")

        return errors

    def get_absolute_url(self) -> str:
        """Get the URL for this page."""
        return self.url

    @property
    def template(self) -> str:
        """Get template name for rendering."""
        return self.template_name or 'flatpages/default.html'


class FlatPageAdmin:
    """
    Admin configuration for FlatPage model.

    Example:
        from faststack.contrib.admin import admin
        from faststack.contrib.flatpages import FlatPageAdmin

        admin.register(FlatPage, FlatPageAdmin)
    """

    list_display = ['url', 'title']
    list_filter = ['registration_required']
    search_fields = ['url', 'title', 'content']
    fields = ['url', 'title', 'content', 'template_name', 'registration_required', 'sites']
