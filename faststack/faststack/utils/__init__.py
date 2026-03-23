"""
FastStack Utils Module - Core utilities.
"""

from .lazy import LazyObject, LazySettings, lazy
from .encoding import (
    urlquote, urlunquote, urljoin,
    iri_to_uri, uri_to_iri,
    escape_uri_path, filepath_to_uri,
    force_str, force_bytes,
)
from .functional import cached_property, cached_method, classproperty

__all__ = [
    # Lazy
    'LazyObject',
    'LazySettings',
    'lazy',
    # Encoding
    'urlquote',
    'urlunquote',
    'urljoin',
    'iri_to_uri',
    'uri_to_iri',
    'escape_uri_path',
    'filepath_to_uri',
    'force_str',
    'force_bytes',
    # Functional
    'cached_property',
    'cached_method',
    'classproperty',
]
