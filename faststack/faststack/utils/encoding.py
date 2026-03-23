"""
Encoding Utilities - URL encoding, IRI/URI conversion.

Example:
    from faststack.utils import urlquote, iri_to_uri, force_str

    encoded = urlquote('hello world')  # 'hello%20world'
    uri = iri_to_uri('/café/')  # '/caf%C3%A9/'
    s = force_str(b'hello')  # 'hello'
"""

from typing import Any, Union
import urllib.parse


def urlquote(url: str, safe: str = '') -> str:
    """
    Quote a URL string.

    Args:
        url: URL to quote
        safe: Characters to not quote

    Returns:
        Quoted URL

    Example:
        urlquote('hello world')  # 'hello%20world'
        urlquote('/path/', safe='/')  # '/path/'
    """
    return urllib.parse.quote(url, safe=safe)


def urlunquote(url: str) -> str:
    """
    Unquote a URL string.

    Args:
        url: URL to unquote

    Returns:
        Unquoted URL
    """
    return urllib.parse.unquote(url)


def urlquote_plus(url: str, safe: str = '') -> str:
    """
    Quote a URL string with plus for spaces.

    Args:
        url: URL to quote
        safe: Characters to not quote

    Returns:
        Quoted URL with + for spaces
    """
    return urllib.parse.quote_plus(url, safe=safe)


def urlunquote_plus(url: str) -> str:
    """Unquote a URL string with plus for spaces."""
    return urllib.parse.unquote_plus(url)


def urljoin(base: str, url: str, allow_fragments: bool = True) -> str:
    """
    Join a base URL with a relative URL.

    Args:
        base: Base URL
        url: Relative URL
        allow_fragments: Allow URL fragments

    Returns:
        Joined URL

    Example:
        urljoin('http://example.com/path/', 'sub/')
        # 'http://example.com/path/sub/'
    """
    return urllib.parse.urljoin(base, url, allow_fragments)


def iri_to_uri(iri: str) -> str:
    """
    Convert an IRI to a URI.

    International Resource Identifiers may contain Unicode characters,
    which need to be percent-encoded for URLs.

    Args:
        iri: IRI string

    Returns:
        URI string

    Example:
        iri_to_uri('/café/')  # '/caf%C3%A9/'
    """
    if iri is None:
        return iri

    # Encode IRI to URI
    # Split into parts and encode each
    parsed = urllib.parse.urlparse(iri)

    # Encode each component
    scheme = parsed.scheme
    netloc = parsed.netloc.encode('idna').decode('ascii') if parsed.netloc else ''
    path = urllib.parse.quote(parsed.path, safe='/:@!$&\'()*+,;=')
    params = urllib.parse.quote(parsed.params, safe='/:@!$&\'()*+,;=')
    query = urllib.parse.quote(parsed.query, safe='/:@!$&\'()*+,;=?')
    fragment = urllib.parse.quote(parsed.fragment, safe='/:@!$&\'()*+,;=?')

    return urllib.parse.urlunparse((scheme, netloc, path, params, query, fragment))


def uri_to_iri(uri: str) -> str:
    """
    Convert a URI to an IRI.

    Args:
        uri: URI string

    Returns:
        IRI string

    Example:
        uri_to_iri('/caf%C3%A9/')  # '/café/'
    """
    if uri is None:
        return uri

    # Decode URI to IRI
    parsed = urllib.parse.urlparse(uri)

    # Decode each component
    scheme = parsed.scheme
    netloc = parsed.netloc.encode('ascii').decode('idna') if parsed.netloc else ''
    path = urllib.parse.unquote(parsed.path)
    params = urllib.parse.unquote(parsed.params)
    query = urllib.parse.unquote(parsed.query)
    fragment = urllib.parse.unquote(parsed.fragment)

    return urllib.parse.urlunparse((scheme, netloc, path, params, query, fragment))


def escape_uri_path(path: str) -> str:
    """
    Escape unsafe characters in a URI path.

    Args:
        path: URI path

    Returns:
        Escaped path
    """
    return urllib.parse.quote(path, safe='/:@!$&\'()*+,;=')


def filepath_to_uri(path: str) -> str:
    """
    Convert a file path to a URI.

    Args:
        path: File path

    Returns:
        URI string
    """
    if path is None:
        return path

    # Normalize separators
    path = path.replace('\\', '/')

    # Encode
    return urllib.parse.quote(path, safe='/:@!$&\'()*+,;=')


def force_str(s: Any, encoding: str = 'utf-8', errors: str = 'strict') -> str:
    """
    Force a value to be a string.

    Args:
        s: Value to convert
        encoding: Encoding to use for bytes
        errors: Error handling strategy

    Returns:
        String value

    Example:
        force_str(b'hello')  # 'hello'
        force_str(123)  # '123'
    """
    if isinstance(s, str):
        return s
    if isinstance(s, bytes):
        return s.decode(encoding, errors)
    return str(s)


def force_bytes(s: Any, encoding: str = 'utf-8', errors: str = 'strict') -> bytes:
    """
    Force a value to be bytes.

    Args:
        s: Value to convert
        encoding: Encoding to use
        errors: Error handling strategy

    Returns:
        Bytes value

    Example:
        force_bytes('hello')  # b'hello'
    """
    if isinstance(s, bytes):
        return s
    if isinstance(s, str):
        return s.encode(encoding, errors)
    return bytes(s)


def is_safe_url(url: str, allowed_hosts: list = None) -> bool:
    """
    Check if a URL is safe for redirection.

    Args:
        url: URL to check
        allowed_hosts: List of allowed hosts

    Returns:
        True if URL is safe
    """
    if url is None:
        return False

    # Allow relative URLs
    if url.startswith('/') and not url.startswith('//'):
        return True

    # Parse URL
    parsed = urllib.parse.urlparse(url)

    # Check scheme
    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        return False

    # Check host
    if parsed.netloc:
        if allowed_hosts is None:
            return False

        host = parsed.netloc.split(':')[0]
        if host not in allowed_hosts:
            return False

    return True


def urlencode(query: Any, doseq: bool = False, safe: str = '', encoding: str = 'utf-8') -> str:
    """
    Encode a dictionary or sequence to a URL query string.

    Args:
        query: Dictionary or sequence to encode
        doseq: Handle sequences as multiple values
        safe: Characters to not encode
        encoding: Encoding for non-ASCII characters

    Returns:
        URL-encoded query string
    """
    if isinstance(query, dict):
        items = query.items()
    else:
        items = query

    # Convert values to strings
    encoded_items = []
    for key, value in items:
        key_str = force_str(key, encoding)
        if doseq and isinstance(value, (list, tuple)):
            for v in value:
                encoded_items.append((key_str, force_str(v, encoding)))
        else:
            encoded_items.append((key_str, force_str(value, encoding)))

    return urllib.parse.urlencode(encoded_items, doseq=doseq, safe=safe, encoding=encoding)
