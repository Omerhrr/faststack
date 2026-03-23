"""
FastStack Sitemaps Framework - SEO sitemap generation.

Example:
    from faststack.contrib.sitemaps import Sitemap, GenericSitemap, SitemapIndex

    class BlogSitemap(Sitemap):
        changefreq = 'weekly'
        priority = 0.7

        def items(self):
            return Post.filter(published=True)

        def location(self, item):
            return f'/blog/{item.slug}/'

        def lastmod(self, item):
            return item.updated_at

    # In routes
    app.route('/sitemap.xml', BlogSitemap())
"""

from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from xml.dom import minidom
import gzip
from urllib.parse import urljoin

from starlette.responses import Response


class Sitemap:
    """
    Base class for sitemaps.

    Attributes:
        changefreq: How often the page changes ('always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never')
        priority: Priority relative to other URLs (0.0 - 1.0)
        limit: Maximum URLs per sitemap
        protocol: URL protocol ('http' or 'https')

    Example:
        class PostSitemap(Sitemap):
            changefreq = 'weekly'
            priority = 0.8

            async def items(self):
                return await Post.filter(published=True)

            def location(self, post):
                return f'/blog/{post.slug}/'

            def lastmod(self, post):
                return post.updated_at
    """

    changefreq: str = 'weekly'
    priority: float = 0.5
    limit: int = 50000
    protocol: str = 'https'

    def __init__(self, request: Any = None):
        self.request = request

    async def __call__(self, scope, receive, send) -> None:
        """ASGI callable for serving sitemap."""
        from starlette.requests import Request
        request = Request(scope, receive)

        # Check if compressed is requested
        accept_encoding = request.headers.get('accept-encoding', '')

        # Generate sitemap
        xml = await self.get_sitemap(request)

        # Optionally compress
        if 'gzip' in accept_encoding:
            xml = gzip.compress(xml.encode('utf-8'))
            response = Response(content=xml, media_type='application/xml', headers={
                'Content-Encoding': 'gzip'
            })
        else:
            response = Response(content=xml, media_type='application/xml')

        await response(scope, receive, send)

    async def get_sitemap(self, request: Any) -> str:
        """Generate sitemap XML."""
        # Get items
        items = self.items()

        if hasattr(items, '__await__'):
            items = await items

        # Limit items
        items = items[:self.limit]

        # Get base URL
        base_url = self._get_base_url(request)

        # Create root element
        urlset = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')

        # Add URLs
        for item in items:
            url = ET.SubElement(urlset, 'url')

            # Location
            loc = self.location(item)
            if not loc.startswith('http'):
                loc = urljoin(base_url, loc)
            ET.SubElement(url, 'loc').text = loc

            # Last modified
            lastmod = self.lastmod(item) if hasattr(self, 'lastmod') else None
            if lastmod:
                ET.SubElement(url, 'lastmod').text = self._iso8601_date(lastmod)

            # Change frequency
            changefreq = self.changefreq
            if hasattr(self, 'get_changefreq'):
                changefreq = self.get_changefreq(item)
            if changefreq:
                ET.SubElement(url, 'changefreq').text = changefreq

            # Priority
            priority = self.priority
            if hasattr(self, 'get_priority'):
                priority = self.get_priority(item)
            if priority is not None:
                ET.SubElement(url, 'priority').text = str(priority)

        # Generate XML string
        rough_string = ET.tostring(urlset, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')

    def _get_base_url(self, request: Any) -> str:
        """Get base URL from request."""
        if hasattr(request, 'url'):
            return f"{request.url.scheme}://{request.url.netloc}"
        return f"{self.protocol}://localhost"

    @staticmethod
    def _iso8601_date(dt: datetime) -> str:
        """Format datetime as ISO 8601."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.date().isoformat()

    def items(self) -> List[Any]:
        """Get sitemap items. Override this method."""
        return []

    def location(self, item: Any) -> str:
        """Get URL for item. Override this method."""
        return str(item)

    def get_urls(self, request: Any = None) -> List[Dict]:
        """
        Get list of URL dictionaries.

        Args:
            request: Request object

        Returns:
            List of URL info dictionaries
        """
        items = self.items()
        base_url = self._get_base_url(request) if request else ''

        urls = []
        for item in items:
            loc = self.location(item)
            if not loc.startswith('http'):
                loc = urljoin(base_url, loc)

            url_info = {
                'location': loc,
                'changefreq': self.changefreq,
                'priority': self.priority,
            }

            if hasattr(self, 'lastmod'):
                url_info['lastmod'] = self.lastmod(item)

            urls.append(url_info)

        return urls


class GenericSitemap(Sitemap):
    """
    Generic sitemap from queryset/list.

    Example:
        sitemap = GenericSitemap(
            queryset=Post.filter(published=True),
            location=lambda post: f'/blog/{post.slug}/',
            lastmod='updated_at',
            priority=0.7
        )
    """

    def __init__(
        self,
        queryset: Any = None,
        location: Callable = None,
        lastmod: Union[str, Callable] = None,
        changefreq: str = 'weekly',
        priority: float = 0.5,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.queryset = queryset
        self._location = location
        self._lastmod = lastmod
        self.changefreq = changefreq
        self.priority = priority

    def items(self) -> List[Any]:
        """Get items from queryset."""
        if self.queryset is None:
            return []
        return self.queryset

    def location(self, item: Any) -> str:
        """Get location for item."""
        if self._location:
            return self._location(item)
        if hasattr(item, 'get_absolute_url'):
            return item.get_absolute_url()
        return f'/{item.pk}/'

    def lastmod(self, item: Any) -> Optional[datetime]:
        """Get last modified for item."""
        if self._lastmod is None:
            return None

        if callable(self._lastmod):
            return self._lastmod(item)

        if isinstance(self._lastmod, str):
            return getattr(item, self._lastmod, None)

        return None


class StaticViewSitemap(Sitemap):
    """
    Sitemap for static views.

    Example:
        sitemap = StaticViewSitemap({
            'home': '/',
            'about': '/about/',
            'contact': '/contact/',
        }, priority=0.5)
    """

    def __init__(
        self,
        views: Dict[str, str],
        priority: float = 0.5,
        changefreq: str = 'monthly',
        **kwargs
    ):
        super().__init__(**kwargs)
        self.views = views
        self.priority = priority
        self.changefreq = changefreq

    def items(self) -> List[Dict]:
        """Return view items."""
        return [
            {'name': name, 'url': url}
            for name, url in self.views.items()
        ]

    def location(self, item: Dict) -> str:
        """Get URL for item."""
        return item['url']


class SitemapIndex:
    """
    Sitemap index for multiple sitemaps.

    Example:
        class MainSitemap(SitemapIndex):
            sitemaps = {
                'posts': PostSitemap,
                'pages': PageSitemap,
                'static': StaticViewSitemap({
                    'home': '/',
                    'about': '/about/',
                }),
            }
    """

    sitemaps: Dict[str, Union[Sitemap, Type[Sitemap]]] = {}
    limit: int = 50000

    def __init__(self, request: Any = None):
        self.request = request

    async def __call__(self, scope, receive, send) -> None:
        """ASGI callable."""
        from starlette.requests import Request
        request = Request(scope, receive)

        # Generate index
        xml = await self.get_sitemap_index(request)

        response = Response(content=xml, media_type='application/xml')
        await response(scope, receive, send)

    async def get_sitemap_index(self, request: Any) -> str:
        """Generate sitemap index XML."""
        base_url = self._get_base_url(request)

        # Create root element
        sitemapindex = ET.Element('sitemapindex', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')

        # Add sitemaps
        for name, sitemap_class in self.sitemaps.items():
            # Handle class or instance
            if isinstance(sitemap_class, type):
                sitemap = sitemap_class(request)
            else:
                sitemap = sitemap_class
                sitemap.request = request

            sitemap_url = ET.SubElement(sitemapindex, 'sitemap')

            # Location
            loc = f"{base_url}/sitemap-{name}.xml"
            ET.SubElement(sitemap_url, 'loc').text = loc

            # Last modified (for the sitemap file)
            if hasattr(sitemap, 'lastmod'):
                lastmod = sitemap.lastmod()
                if lastmod:
                    ET.SubElement(sitemap_url, 'lastmod').text = Sitemap._iso8601_date(lastmod)

        # Generate XML string
        rough_string = ET.tostring(sitemapindex, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')

    def _get_base_url(self, request: Any) -> str:
        """Get base URL from request."""
        if hasattr(request, 'url'):
            return f"{request.url.scheme}://{request.url.netloc}"
        return 'https://localhost'

    def get_urls(self, request: Any = None) -> List[Dict]:
        """Get all URLs from all sitemaps."""
        base_url = self._get_base_url(request) if request else ''

        urls = []
        for name, sitemap_class in self.sitemaps.items():
            if isinstance(sitemap_class, type):
                sitemap = sitemap_class(request)
            else:
                sitemap = sitemap_class

            urls.append({
                'location': f"{base_url}/sitemap-{name}.xml",
            })

        return urls


class RobotsTxt:
    """
    Generate robots.txt.

    Example:
        class Robots(RobotsTxt):
            sitemap_url = '/sitemap.xml'

            def rules(self):
                return [
                    Rule(allow='/'),
                    Rule(disallow='/admin/'),
                    Rule(disallow='/api/', user_agent='*'),
                    Rule(allow='/api/public/', user_agent='*'),
                ]
    """

    sitemap_url: str = '/sitemap.xml'
    crawl_delay: float = None

    def __init__(self, request: Any = None):
        self.request = request

    async def __call__(self, scope, receive, send) -> None:
        """ASGI callable."""
        content = self.generate()
        response = Response(content=content, media_type='text/plain')
        await response(scope, receive, send)

    def generate(self) -> str:
        """Generate robots.txt content."""
        lines = []

        # Add rules
        for rule in self.rules():
            if rule.user_agent:
                lines.append(f"User-agent: {rule.user_agent}")
            else:
                lines.append("User-agent: *")

            for allow in rule.allows:
                lines.append(f"Allow: {allow}")

            for disallow in rule.disallows:
                lines.append(f"Disallow: {disallow}")

            if rule.crawl_delay:
                lines.append(f"Crawl-delay: {rule.crawl_delay}")

            lines.append("")

        # Add sitemap
        if self.sitemap_url:
            if not self.sitemap_url.startswith('http'):
                # Make absolute
                self.sitemap_url = f"https://example.com{self.sitemap_url}"
            lines.append(f"Sitemap: {self.sitemap_url}")

        return '\n'.join(lines)

    def rules(self) -> List['Rule']:
        """Get robot rules. Override this method."""
        return [Rule(allow='/')]


class Rule:
    """Robot rule."""

    def __init__(
        self,
        allow: str = None,
        disallow: str = None,
        user_agent: str = '*',
        crawl_delay: float = None
    ):
        self.allows = [allow] if allow else []
        self.disallows = [disallow] if disallow else []
        self.user_agent = user_agent
        self.crawl_delay = crawl_delay

    def add_allow(self, path: str):
        """Add allowed path."""
        self.allows.append(path)

    def add_disallow(self, path: str):
        """Add disallowed path."""
        self.disallows.append(path)
