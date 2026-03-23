"""
Internationalization Utilities

Helper functions for language detection and management.
"""

import re
from typing import Any


def get_supported_language_variant(
    lang_code: str,
    supported_languages: list[str],
    strict: bool = False,
) -> str | None:
    """
    Return the language code from supported languages that matches lang_code.
    
    If exact match, returns lang_code.
    If variant (e.g., 'de-at' for 'de'), returns that.
    If no match, returns None.
    
    Args:
        lang_code: Language code to find variant for
        supported_languages: List of supported language codes
        strict: If True, only return exact matches
    
    Returns:
        Matching language code or None
    """
    if lang_code in supported_languages:
        return lang_code
    
    if strict:
        return None
    
    # Try to find a variant
    # First, try with underscore variant (de_AT -> de-at)
    normalized = lang_code.replace('_', '-').lower()
    
    for supported in supported_languages:
        supported_lower = supported.lower()
        if supported_lower == normalized:
            return supported
        
        # Check if language part matches
        supported_primary = supported_lower.split('-')[0]
        lang_primary = normalized.split('-')[0]
        
        if supported_primary == lang_primary:
            return supported
    
    return None


def check_for_language(lang_code: str) -> bool:
    """
    Check if a language code is valid.
    
    Checks against common language patterns.
    
    Args:
        lang_code: Language code to check
    
    Returns:
        True if the code looks like a valid language code
    """
    if not lang_code:
        return False
    
    # Basic pattern: 2-3 letter language code, optionally with region
    # Examples: en, de, zh-CN, pt_BR, en-US
    pattern = re.compile(r'^[a-z]{2,3}(?:[-_][a-z]{2,4})?$', re.IGNORECASE)
    return bool(pattern.match(lang_code))


def to_locale(language: str) -> str:
    """
    Convert a language code to locale format.
    
    'en-us' -> 'en_US'
    'zh_CN' -> 'zh_CN'
    
    Args:
        language: Language code
    
    Returns:
        Locale-formatted string
    """
    p = language.find('-')
    if p >= 0:
        return f"{language[:p]}_{language[p+1:].upper()}"
    return language


def to_language(locale: str) -> str:
    """
    Convert a locale to language code format.
    
    'en_US' -> 'en-us'
    'zh_CN' -> 'zh-cn'
    
    Args:
        locale: Locale string
    
    Returns:
        Language code string
    """
    p = locale.find('_')
    if p >= 0:
        return f"{locale[:p]}-{locale[p+1:].lower()}"
    return locale


def get_language_from_path(path: str, supported_languages: list[str]) -> str | None:
    """
    Extract language code from URL path.
    
    /en/about/ -> 'en'
    /de/ueber-uns/ -> 'de'
    /about/ -> None
    
    Args:
        path: URL path
        supported_languages: List of supported languages
    
    Returns:
        Language code or None
    """
    pattern = re.compile(r'^/(\w{2,3}(?:[-_]\w{2,4})?)(/|$)')
    match = pattern.match(path)
    
    if match:
        lang_code = match.group(1)
        if lang_code in supported_languages:
            return lang_code
    
    return None


def parse_accept_lang_header(accept_language: str) -> list[tuple[str, float]]:
    """
    Parse the Accept-Language header.
    
    Returns list of (language, quality) tuples sorted by quality.
    
    Args:
        accept_language: Accept-Language header value
    
    Returns:
        List of (language, quality) tuples
    """
    result = []
    
    for part in accept_language.split(','):
        part = part.strip()
        if not part:
            continue
        
        if ';' in part:
            lang, params = part.split(';', 1)
            q = 1.0
            
            for param in params.split(';'):
                param = param.strip()
                if param.startswith('q='):
                    try:
                        q = float(param[2:])
                    except ValueError:
                        q = 1.0
        else:
            lang = part
            q = 1.0
        
        lang = lang.strip()
        if lang and lang != '*':
            result.append((lang, q))
    
    # Sort by quality (descending)
    result.sort(key=lambda x: -x[1])
    return result


def get_languages_info() -> dict[str, dict[str, Any]]:
    """
    Get information about all supported languages.
    
    Returns:
        Dictionary of language_code -> info dict
    """
    from faststack.core.i18n.translation import get_language_info
    
    from faststack.config import settings
    supported = getattr(settings, 'LANGUAGES', [('en', 'English')])
    
    result = {}
    for code, name in supported:
        info = get_language_info(code)
        info['name'] = name  # Use configured name
        result[code] = info
    
    return result


def format_date(
    value,
    format_string: str | None = None,
    use_l10n: bool = True,
):
    """
    Format a date according to locale.
    
    Args:
        value: Date value (datetime or string)
        format_string: Optional format string
        use_l10n: Whether to use localized format
    
    Returns:
        Formatted date string
    """
    from datetime import datetime
    
    if isinstance(value, str):
        # Try to parse
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    
    if not hasattr(value, 'strftime'):
        return str(value)
    
    if format_string:
        return value.strftime(format_string)
    
    # Use locale-specific format
    from faststack.core.i18n.translation import get_language
    lang = get_language() or 'en'
    
    # Common date formats by locale
    formats = {
        'en': '%B %d, %Y',  # January 15, 2024
        'de': '%d.%m.%Y',   # 15.01.2024
        'fr': '%d/%m/%Y',   # 15/01/2024
        'ja': '%Y年%m月%d日',  # 2024年01月15日
        'zh': '%Y年%m月%d日',  # 2024年01月15日
    }
    
    fmt = formats.get(lang, formats['en'])
    return value.strftime(fmt)


def format_time(
    value,
    format_string: str | None = None,
    use_l10n: bool = True,
):
    """
    Format a time according to locale.
    
    Args:
        value: Time value
        format_string: Optional format string
        use_l10n: Whether to use localized format
    
    Returns:
        Formatted time string
    """
    from datetime import datetime, time as time_type
    
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value).time()
        except ValueError:
            return value
    
    if isinstance(value, datetime):
        value = value.time()
    
    if not hasattr(value, 'strftime'):
        return str(value)
    
    if format_string:
        return value.strftime(format_string)
    
    # Use locale-specific format
    from faststack.core.i18n.translation import get_language
    lang = get_language() or 'en'
    
    formats = {
        'en': '%I:%M %p',   # 03:30 PM
        'de': '%H:%M',      # 15:30
        'fr': '%H:%M',      # 15:30
        'ja': '%H:%M',      # 15:30
        'zh': '%H:%M',      # 15:30
    }
    
    fmt = formats.get(lang, formats['en'])
    return value.strftime(fmt)


def format_number(value, decimal_places: int | None = None) -> str:
    """
    Format a number according to locale.
    
    Args:
        value: Numeric value
        decimal_places: Number of decimal places
    
    Returns:
        Formatted number string
    """
    from faststack.core.i18n.translation import get_language
    lang = get_language() or 'en'
    
    try:
        if decimal_places is not None:
            value = float(value)
            value = round(value, decimal_places)
        else:
            value = float(value)
    except (TypeError, ValueError):
        return str(value)
    
    # Locale-specific formatting
    if lang in ('de', 'de_DE', 'de_AT'):
        # German: 1.234,56
        return f"{value:,.{decimal_places or 2}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    elif lang in ('fr', 'fr_FR'):
        # French: 1 234,56
        formatted = f"{value:,.{decimal_places or 2}f}"
        return formatted.replace(',', ' ').replace('.', ',')
    else:
        # English default: 1,234.56
        return f"{value:,.{decimal_places or 2}f}"
