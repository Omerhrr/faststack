"""
FastStack Syndication Framework - RSS/Atom feed generation.

Example:
    from faststack.contrib.syndication import Feed, Rss201rev2Feed, Atom1Feed

    class LatestPostsFeed(Feed):
        title = "My Blog"
        link = "/blog/"
        description = "Latest blog posts"

        def items(self):
            return Post.all().order_by('-created_at')[:20]

        def item_title(self, item):
            return item.title

        def item_description(self, item):
            return item.excerpt

        def item_link(self, item):
            return f"/blog/{item.slug}/"

    # In routes
    app.route('/feeds/latest/', LatestPostsFeed())
"""

from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from xml.dom import minidom
import email.utils
import html
import re

from starlette.responses import Response


class Feed:
    """
    Base class for feed generation.

    Subclass this to create custom feeds.

    Attributes:
        title: Feed title
        link: Feed link
        description: Feed description
        author_name: Author name
        author_email: Author email
        author_link: Author URL
        language: Feed language
        categories: List of categories
        feed_type: Feed type class

    Example:
        class LatestPostsFeed(Feed):
            title = "My Blog Posts"
            link = "/blog/"
            description = "Latest posts from my blog"

            async def items(self):
                return await Post.all().order_by('-created_at')[:20]

            def item_title(self, item):
                return item.title

            def item_description(self, item):
                return item.excerpt or item.content[:200]

            def item_link(self, item):
                return f"/blog/{item.slug}/"

            def item_pubdate(self, item):
                return item.created_at
    """

    # Feed metadata
    title: str = ''
    link: str = ''
    description: str = ''
    author_name: str = ''
    author_email: str = ''
    author_link: str = ''
    language: str = 'en'
    categories: List[str] = []
    feed_url: str = ''

    # Feed type
    feed_type: Type['BaseFeed'] = None

    # Item limit
    limit: int = 20

    def __init__(self, request: Any = None):
        self.request = request

        # Default to RSS 2.0
        if self.feed_type is None:
            self.feed_type = Rss201rev2Feed

    async def __call__(self, scope, receive, send) -> None:
        """ASGI callable for serving feed."""
        from starlette.requests import Request
        request = Request(scope, receive)

        # Generate feed
        feed = await self.get_feed(request)

        # Create response
        response = Response(
            content=feed.writeString('utf-8'),
            media_type=feed.content_type
        )

        await response(scope, receive, send)

    async def get_feed(self, request: Any) -> 'BaseFeed':
        """
        Generate the feed.

        Args:
            request: Request object

        Returns:
            Feed instance
        """
        # Create feed
        feed = self.feed_type(
            title=self.title,
            link=self.link,
            description=self.description,
            language=self.language,
            author_name=self.author_name,
            author_email=self.author_email,
            author_link=self.author_link,
            feed_url=self.feed_url or self._get_feed_url(request),
        )

        # Add categories
        for category in self.categories:
            feed.add_category(category)

        # Get items
        items = self.items()

        # Handle async items
        if hasattr(items, '__await__'):
            items = await items

        # Limit items
        items = items[:self.limit]

        # Add items to feed
        for item in items:
            feed.add_item(
                title=self.item_title(item),
                link=self.item_link(item),
                description=self.item_description(item),
                author_name=self.item_author_name(item) if hasattr(self, 'item_author_name') else None,
                author_email=self.item_author_email(item) if hasattr(self, 'item_author_email') else None,
                author_link=self.item_author_link(item) if hasattr(self, 'item_author_link') else None,
                pubdate=self.item_pubdate(item) if hasattr(self, 'item_pubdate') else None,
                updateddate=self.item_updateddate(item) if hasattr(self, 'item_updateddate') else None,
                categories=self.item_categories(item) if hasattr(self, 'item_categories') else None,
                enclosures=self.item_enclosures(item) if hasattr(self, 'item_enclosures') else None,
                comments=self.item_comments(item) if hasattr(self, 'item_comments') else None,
                unique_id=self.item_unique_id(item) if hasattr(self, 'item_unique_id') else None,
                unique_id_is_permalink=self.item_unique_id_is_permalink(item) if hasattr(self, 'item_unique_id_is_permalink') else True,
                content=self.item_content(item) if hasattr(self, 'item_content') else None,
                extra_kwargs=self.item_extra_kwargs(item) if hasattr(self, 'item_extra_kwargs') else None,
            )

        return feed

    def _get_feed_url(self, request: Any) -> str:
        """Get the full feed URL from request."""
        if hasattr(request, 'url'):
            return str(request.url)
        return self.link

    def items(self) -> List[Any]:
        """Get feed items. Override this method."""
        return []

    def item_title(self, item: Any) -> str:
        """Get item title."""
        return str(item)

    def item_link(self, item: Any) -> str:
        """Get item link."""
        return ''

    def item_description(self, item: Any) -> str:
        """Get item description."""
        return ''


class BaseFeed:
    """Base class for feed types."""

    content_type: str = 'application/xml'

    def __init__(
        self,
        title: str,
        link: str,
        description: str = '',
        language: str = 'en',
        author_name: str = '',
        author_email: str = '',
        author_link: str = '',
        feed_url: str = '',
        **kwargs
    ):
        self.title = title
        self.link = link
        self.description = description
        self.language = language
        self.author_name = author_name
        self.author_email = author_email
        self.author_link = author_link
        self.feed_url = feed_url
        self.categories: List[str] = []
        self.items: List[Dict] = []

    def add_category(self, category: str):
        """Add a category to the feed."""
        self.categories.append(category)

    def add_item(self, **kwargs):
        """Add an item to the feed."""
        self.items.append(kwargs)

    def writeString(self, encoding: str = 'utf-8') -> str:
        """Write feed to string."""
        raise NotImplementedError()


class Rss201rev2Feed(BaseFeed):
    """
    RSS 2.0.1 feed generator.

    Example:
        feed = Rss201rev2Feed(
            title="My Blog",
            link="https://example.com/blog/",
            description="Latest posts"
        )
        feed.add_item(title="Hello", link="/hello/", description="First post")
        xml = feed.writeString('utf-8')
    """

    content_type = 'application/rss+xml'

    def writeString(self, encoding: str = 'utf-8') -> str:
        """Generate RSS XML."""
        # Create root element
        rss = ET.Element('rss', version='2.0', attrib={
            'xmlns:atom': 'http://www.w3.org/2005/Atom',
            'xmlns:content': 'http://purl.org/rss/1.0/modules/content/',
        })

        channel = ET.SubElement(rss, 'channel')

        # Channel metadata
        ET.SubElement(channel, 'title').text = self.title
        ET.SubElement(channel, 'link').text = self.link
        ET.SubElement(channel, 'description').text = self.description

        if self.language:
            ET.SubElement(channel, 'language').text = self.language

        if self.feed_url:
            atom_link = ET.SubElement(channel, 'atom:link')
            atom_link.set('href', self.feed_url)
            atom_link.set('rel', 'self')
            atom_link.set('type', 'application/rss+xml')

        if self.author_email:
            ET.SubElement(channel, 'managingEditor').text = self.author_email

        if self.author_name:
            ET.SubElement(channel, 'webMaster').text = self.author_email or ''

        # Categories
        for category in self.categories:
            ET.SubElement(channel, 'category').text = category

        # Last build date
        ET.SubElement(channel, 'lastBuildDate').text = self._rfc2822_date(datetime.now(timezone.utc))

        # Items
        for item_data in self.items:
            item = ET.SubElement(channel, 'item')

            # Title
            if item_data.get('title'):
                ET.SubElement(item, 'title').text = item_data['title']

            # Link
            if item_data.get('link'):
                ET.SubElement(item, 'link').text = item_data['link']

            # Description
            if item_data.get('description'):
                ET.SubElement(item, 'description').text = item_data['description']

            # Content (encoded)
            if item_data.get('content'):
                content = ET.SubElement(item, 'content:encoded')
                content.text = item_data['content']

            # Author
            author = []
            if item_data.get('author_email'):
                author.append(item_data['author_email'])
            if item_data.get('author_name'):
                author.append(f" ({item_data['author_name']})")
            if author:
                ET.SubElement(item, 'author').text = ''.join(author)

            # Categories
            for category in item_data.get('categories', []):
                ET.SubElement(item, 'category').text = category

            # PubDate
            if item_data.get('pubdate'):
                ET.SubElement(item, 'pubDate').text = self._rfc2822_date(item_data['pubdate'])

            # GUID
            unique_id = item_data.get('unique_id')
            if unique_id:
                guid = ET.SubElement(item, 'guid')
                guid.text = unique_id
                is_permalink = item_data.get('unique_id_is_permalink', True)
                if not is_permalink:
                    guid.set('isPermaLink', 'false')
            elif item_data.get('link'):
                ET.SubElement(item, 'guid').text = item_data['link']

            # Comments
            if item_data.get('comments'):
                ET.SubElement(item, 'comments').text = item_data['comments']

            # Enclosures
            for enclosure in item_data.get('enclosures', []):
                enc = ET.SubElement(item, 'enclosure')
                enc.set('url', enclosure.get('url', ''))
                enc.set('length', str(enclosure.get('length', 0)))
                enc.set('type', enclosure.get('mime_type', 'application/octet-stream'))

        # Generate XML string
        rough_string = ET.tostring(rss, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='  ', encoding=encoding).decode(encoding)

    @staticmethod
    def _rfc2822_date(dt: datetime) -> str:
        """Format datetime as RFC 2822."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return email.utils.format_datetime(dt)


class Atom1Feed(BaseFeed):
    """
    Atom 1.0 feed generator.

    Example:
        feed = Atom1Feed(
            title="My Blog",
            link="https://example.com/blog/",
            description="Latest posts"
        )
        feed.add_item(title="Hello", link="/hello/", description="First post")
        xml = feed.writeString('utf-8')
    """

    content_type = 'application/atom+xml'

    def writeString(self, encoding: str = 'utf-8') -> str:
        """Generate Atom XML."""
        # Create root element
        feed = ET.Element('feed', xmlns='http://www.w3.org/2005/Atom')

        # Title
        ET.SubElement(feed, 'title').text = self.title

        # Link (alternate)
        link = ET.SubElement(feed, 'link')
        link.set('rel', 'alternate')
        link.set('href', self.link)

        # Self link
        if self.feed_url:
            self_link = ET.SubElement(feed, 'link')
            self_link.set('rel', 'self')
            self_link.set('href', self.feed_url)

        # ID
        ET.SubElement(feed, 'id').text = self.link

        # Updated
        ET.SubElement(feed, 'updated').text = self._iso8601_date(datetime.now(timezone.utc))

        # Subtitle
        if self.description:
            ET.SubElement(feed, 'subtitle').text = self.description

        # Author
        if self.author_name or self.author_email:
            author = ET.SubElement(feed, 'author')
            if self.author_name:
                ET.SubElement(author, 'name').text = self.author_name
            if self.author_email:
                ET.SubElement(author, 'email').text = self.author_email
            if self.author_link:
                ET.SubElement(author, 'uri').text = self.author_link

        # Categories
        for category in self.categories:
            cat = ET.SubElement(feed, 'category')
            cat.set('term', category)

        # Generator
        generator = ET.SubElement(feed, 'generator')
        generator.text = 'FastStack'
        generator.set('uri', 'https://github.com/faststack/faststack')

        # Entries
        for item_data in self.items:
            entry = ET.SubElement(feed, 'entry')

            # Title
            ET.SubElement(entry, 'title').text = item_data.get('title', '')

            # Link
            if item_data.get('link'):
                link = ET.SubElement(entry, 'link')
                link.set('href', item_data['link'])

            # ID
            unique_id = item_data.get('unique_id') or item_data.get('link')
            if unique_id:
                ET.SubElement(entry, 'id').text = unique_id

            # Updated
            updated = item_data.get('updateddate') or item_data.get('pubdate') or datetime.now(timezone.utc)
            ET.SubElement(entry, 'updated').text = self._iso8601_date(updated)

            # Published
            if item_data.get('pubdate'):
                ET.SubElement(entry, 'published').text = self._iso8601_date(item_data['pubdate'])

            # Author
            if item_data.get('author_name') or item_data.get('author_email'):
                author = ET.SubElement(entry, 'author')
                if item_data.get('author_name'):
                    ET.SubElement(author, 'name').text = item_data['author_name']
                if item_data.get('author_email'):
                    ET.SubElement(author, 'email').text = item_data['author_email']

            # Content
            if item_data.get('content'):
                content = ET.SubElement(entry, 'content')
                content.set('type', 'html')
                content.text = item_data['content']
            elif item_data.get('description'):
                content = ET.SubElement(entry, 'content')
                content.set('type', 'html')
                content.text = item_data['description']

            # Summary
            if item_data.get('description') and item_data.get('content'):
                ET.SubElement(entry, 'summary').text = item_data['description']

            # Categories
            for category in item_data.get('categories', []):
                cat = ET.SubElement(entry, 'category')
                cat.set('term', category)

        # Generate XML string
        rough_string = ET.tostring(feed, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='  ', encoding=encoding).decode(encoding)

    @staticmethod
    def _iso8601_date(dt: datetime) -> str:
        """Format datetime as ISO 8601."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class JsonFeed(BaseFeed):
    """
    JSON Feed 1.1 generator.

    Example:
        feed = JsonFeed(
            title="My Blog",
            link="https://example.com/blog/",
            description="Latest posts"
        )
        feed.add_item(title="Hello", link="/hello/", description="First post")
        json_str = feed.writeString('utf-8')
    """

    content_type = 'application/feed+json'

    def writeString(self, encoding: str = 'utf-8') -> str:
        """Generate JSON Feed."""
        import json

        feed_data = {
            'version': 'https://jsonfeed.org/version/1.1',
            'title': self.title,
            'home_page_url': self.link,
        }

        if self.feed_url:
            feed_data['feed_url'] = self.feed_url

        if self.description:
            feed_data['description'] = self.description

        if self.author_name or self.author_email:
            feed_data['authors'] = []
            author = {}
            if self.author_name:
                author['name'] = self.author_name
            if self.author_email:
                author['url'] = f'mailto:{self.author_email}'
            if self.author_link:
                author['url'] = self.author_link
            feed_data['authors'].append(author)

        # Items
        feed_data['items'] = []
        for item_data in self.items:
            item = {}

            if item_data.get('unique_id'):
                item['id'] = item_data['unique_id']
            elif item_data.get('link'):
                item['id'] = item_data['link']

            if item_data.get('link'):
                item['url'] = item_data['link']

            if item_data.get('title'):
                item['title'] = item_data['title']

            if item_data.get('description'):
                item['summary'] = item_data['description']

            if item_data.get('content'):
                item['content_html'] = item_data['content']

            if item_data.get('pubdate'):
                item['date_published'] = self._iso8601_date(item_data['pubdate'])

            if item_data.get('updateddate'):
                item['date_modified'] = self._iso8601_date(item_data['updateddate'])

            if item_data.get('author_name') or item_data.get('author_email'):
                item['authors'] = []
                author = {}
                if item_data.get('author_name'):
                    author['name'] = item_data['author_name']
                if item_data.get('author_email'):
                    author['url'] = f'mailto:{item_data["author_email"]}'
                item['authors'].append(author)

            if item_data.get('categories'):
                item['tags'] = item_data['categories']

            feed_data['items'].append(item)

        return json.dumps(feed_data, indent=2, default=str)

    @staticmethod
    def _iso8601_date(dt: datetime) -> str:
        """Format datetime as ISO 8601."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
