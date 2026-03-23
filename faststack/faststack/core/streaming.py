"""
FastStack Streaming Responses - File streaming and large responses.

Example:
    from faststack.core.streaming import (
        StreamingResponse,
        FileResponse,
        AsyncFileResponse,
        iter_chunks,
        stream_from_generator
    )

    # Stream a generator
    async def generate():
        for i in range(1000):
            yield f"Item {i}\n"

    response = StreamingResponse(generate())

    # Stream a file
    response = FileResponse('/path/to/file.pdf')

    # Stream with progress
    response = StreamingResponse(
        iter_chunks(large_data, chunk_size=8192),
        media_type='application/octet-stream'
    )
"""

from typing import Any, AsyncIterator, Callable, Dict, Iterator, Optional, Union
from pathlib import Path
import os
import asyncio
import mimetypes

from starlette.responses import Response


class StreamingResponse(Response):
    """
    Response that streams content from an iterator.

    Example:
        async def generate_csv():
            yield 'name,value\n'
            for item in items:
                yield f'{item.name},{item.value}\n'

        return StreamingResponse(
            generate_csv(),
            media_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename=data.csv'}
        )
    """

    def __init__(
        self,
        content: Union[Iterator, AsyncIterator],
        status_code: int = 200,
        headers: Dict[str, str] = None,
        media_type: str = None,
    ):
        """
        Initialize StreamingResponse.

        Args:
            content: Iterator or async iterator yielding content
            status_code: HTTP status code
            headers: Response headers
            media_type: Content media type
        """
        super().__init__(
            content=b'',
            status_code=status_code,
            headers=headers,
            media_type=media_type
        )
        self.body_iterator = content

    async def __call__(self, scope, receive, send):
        """Send the streaming response."""
        await send({
            'type': 'http.response.start',
            'status': self.status_code,
            'headers': self._build_headers(),
        })

        # Stream body
        if asyncio.iscoroutinefunction(self.body_iterator):
            # It's an async generator
            async for chunk in self.body_iterator():
                if isinstance(chunk, str):
                    chunk = chunk.encode('utf-8')
                await send({
                    'type': 'http.response.body',
                    'body': chunk,
                    'more_body': True,
                })
        else:
            # It's a regular generator or async generator
            async for chunk in self._aiter():
                if isinstance(chunk, str):
                    chunk = chunk.encode('utf-8')
                await send({
                    'type': 'http.response.body',
                    'body': chunk,
                    'more_body': True,
                })

        # Send final empty chunk
        await send({
            'type': 'http.response.body',
            'body': b'',
            'more_body': False,
        })

    async def _aiter(self):
        """Iterate over body, handling both sync and async iterators."""
        if hasattr(self.body_iterator, '__aiter__'):
            async for chunk in self.body_iterator:
                yield chunk
        else:
            for chunk in self.body_iterator:
                yield chunk


class FileResponse(Response):
    """
    Response for serving files.

    Supports range requests, ETags, and conditional responses.

    Example:
        return FileResponse(
            '/path/to/file.pdf',
            filename='document.pdf',
            content_disposition='attachment'
        )
    """

    chunk_size = 64 * 1024  # 64KB chunks

    def __init__(
        self,
        path: Union[str, Path],
        status_code: int = 200,
        headers: Dict[str, str] = None,
        media_type: str = None,
        filename: str = None,
        content_disposition: str = None,
        stat_result: os.stat_result = None,
        method: str = None,
    ):
        """
        Initialize FileResponse.

        Args:
            path: Path to file
            status_code: HTTP status code
            headers: Response headers
            media_type: Content media type
            filename: Filename for Content-Disposition
            content_disposition: 'attachment' or 'inline'
            stat_result: Pre-computed stat result
            method: HTTP method (for HEAD support)
        """
        self.path = Path(path)
        self.filename = filename or self.path.name
        self.method = method or 'GET'
        self.stat_result = stat_result or os.stat(self.path)

        # Determine media type
        if media_type is None:
            media_type, _ = mimetypes.guess_type(self.path.name)
            media_type = media_type or 'application/octet-stream'

        # Build headers
        headers = headers or {}
        headers.setdefault('content-length', str(self.stat_result.st_size))
        headers.setdefault('last-modified', self._http_date(self.stat_result.st_mtime))
        headers.setdefault('etag', self._generate_etag())

        if content_disposition:
            headers['content-disposition'] = f'{content_disposition}; filename="{self.filename}"'

        super().__init__(
            content=b'',
            status_code=status_code,
            headers=headers,
            media_type=media_type
        )

    @staticmethod
    def _http_date(timestamp: float) -> str:
        """Convert timestamp to HTTP date format."""
        from email.utils import formatdate
        return formatdate(timestamp, usegmt=True)

    def _generate_etag(self) -> str:
        """Generate ETag from file stats."""
        return f'"{self.stat_result.st_size}-{int(self.stat_result.st_mtime)}"'

    async def __call__(self, scope, receive, send):
        """Send the file response."""
        # Check for conditional request
        request_headers = dict(scope.get('headers', []))
        if_none_match = request_headers.get(b'if-none-match', b'').decode()
        if_modified_since = request_headers.get(b'if-modified-since', b'').decode()

        etag = self._generate_etag()
        if if_none_match:
            if etag in if_none_match or '*' in if_none_match:
                await send({
                    'type': 'http.response.start',
                    'status': 304,
                    'headers': [],
                })
                await send({'type': 'http.response.body'})
                return

        # Check for range request
        range_header = request_headers.get(b'range', b'').decode()
        if range_header:
            await self._send_range(scope, receive, send, range_header)
            return

        # Send headers
        await send({
            'type': 'http.response.start',
            'status': self.status_code,
            'headers': self._build_headers(),
        })

        # Send file content (HEAD request doesn't need body)
        if self.method != 'HEAD':
            with open(self.path, 'rb') as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    await send({
                        'type': 'http.response.body',
                        'body': chunk,
                        'more_body': True,
                    })

        # Send final chunk
        await send({
            'type': 'http.response.body',
            'body': b'',
            'more_body': False,
        })

    async def _send_range(self, scope, receive, send, range_header: str):
        """Handle range request."""
        import re

        match = re.match(r'bytes=(\d*)-(\d*)', range_header)
        if not match:
            # Invalid range
            await send({
                'type': 'http.response.start',
                'status': 416,
                'headers': [(b'content-range', f'bytes */{self.stat_result.st_size}'.encode())],
            })
            await send({'type': 'http.response.body'})
            return

        start, end = match.groups()
        file_size = self.stat_result.st_size

        if start:
            start = int(start)
        else:
            start = file_size - int(end)
            end = file_size - 1

        if end:
            end = int(end) + 1  # Make end exclusive
        else:
            end = file_size

        # Validate range
        if start >= file_size or end > file_size or start >= end:
            await send({
                'type': 'http.response.start',
                'status': 416,
                'headers': [(b'content-range', f'bytes */{file_size}'.encode())],
            })
            await send({'type': 'http.response.body'})
            return

        # Build headers
        headers = self._build_headers()
        headers.append((b'content-range', f'bytes {start}-{end-1}/{file_size}'.encode()))
        headers.append((b'content-length', str(end - start).encode()))

        await send({
            'type': 'http.response.start',
            'status': 206,  # Partial Content
            'headers': headers,
        })

        # Send range content
        with open(self.path, 'rb') as f:
            f.seek(start)
            remaining = end - start
            while remaining > 0:
                chunk_size = min(self.chunk_size, remaining)
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                remaining -= len(chunk)
                await send({
                    'type': 'http.response.body',
                    'body': chunk,
                    'more_body': True,
                })

        await send({
            'type': 'http.response.body',
            'body': b'',
            'more_body': False,
        })


class AsyncFileResponse(Response):
    """
    Async file response using aiofiles.

    Example:
        return AsyncFileResponse('/path/to/large/file.iso')
    """

    chunk_size = 64 * 1024

    def __init__(self, path: Union[str, Path], **kwargs):
        self.path = Path(path)
        super().__init__(content=b'', **kwargs)

    async def __call__(self, scope, receive, send):
        """Send file asynchronously."""
        try:
            import aiofiles
        except ImportError:
            # Fall back to sync FileResponse
            response = FileResponse(self.path, status_code=self.status_code)
            await response(scope, receive, send)
            return

        stat_result = self.path.stat()
        headers = self._build_headers()
        headers.append((b'content-length', str(stat_result.st_size).encode()))

        await send({
            'type': 'http.response.start',
            'status': self.status_code,
            'headers': headers,
        })

        async with aiofiles.open(self.path, 'rb') as f:
            while True:
                chunk = await f.read(self.chunk_size)
                if not chunk:
                    break
                await send({
                    'type': 'http.response.body',
                    'body': chunk,
                    'more_body': True,
                })

        await send({
            'type': 'http.response.body',
            'body': b'',
            'more_body': False,
        })


async def iter_chunks(
    content: Union[bytes, str, Iterator, AsyncIterator],
    chunk_size: int = 8192
) -> AsyncIterator[bytes]:
    """
    Iterate over content in chunks.

    Args:
        content: Content to chunk
        chunk_size: Size of each chunk

    Yields:
        Bytes chunks
    """
    if isinstance(content, str):
        content = content.encode('utf-8')

    if isinstance(content, bytes):
        for i in range(0, len(content), chunk_size):
            yield content[i:i + chunk_size]
    elif hasattr(content, '__aiter__'):
        async for chunk in content:
            if isinstance(chunk, str):
                chunk = chunk.encode('utf-8')
            for i in range(0, len(chunk), chunk_size):
                yield chunk[i:i + chunk_size]
    else:
        for chunk in content:
            if isinstance(chunk, str):
                chunk = chunk.encode('utf-8')
            for i in range(0, len(chunk), chunk_size):
                yield chunk[i:i + chunk_size]


def stream_from_generator(
    generator: Union[Callable, Iterator, AsyncIterator],
    chunk_size: int = 8192
) -> StreamingResponse:
    """
    Create a StreamingResponse from a generator.

    Args:
        generator: Generator function or iterator
        chunk_size: Chunk size

    Returns:
        StreamingResponse
    """
    if callable(generator):
        generator = generator()

    async def aiter():
        for chunk in iter_chunks(generator, chunk_size):
            yield chunk

    return StreamingResponse(aiter())
