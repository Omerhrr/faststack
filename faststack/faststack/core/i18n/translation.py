"""
Translation Functions

Core translation functionality for FastStack i18n.
"""

import os
import threading
from pathlib import Path
from typing import Any
from functools import lru_cache


# Thread-local storage for active language
_active = threading.local()

# Session key for storing language preference
LANGUAGE_SESSION_KEY = "_language"


class Translation:
    """
    Translation class that handles a single language's translations.
    
    Loads translations from .mo (compiled message) files and provides
    methods for looking up translations.
    """
    
    def __init__(self, language: str, translation_dir: Path | None = None):
        """
        Initialize translation for a language.
        
        Args:
            language: Language code (e.g., 'de', 'fr', 'zh_CN')
            translation_dir: Directory containing translation files
        """
        self.language = language
        self.translation_dir = translation_dir
        self._catalog: dict[str, str] = {}
        self._plural_catalog: dict[str, dict[int, str]] = {}
        
        if translation_dir:
            self._load_translations()
    
    def _load_translations(self) -> None:
        """Load translations from .mo files."""
        # Try to find and load the .mo file
        mo_file = self.translation_dir / self.language / "LC_MESSAGES" / "django.mo"
        
        if not mo_file.exists():
            # Try without django prefix
            mo_file = self.translation_dir / self.language / "LC_MESSAGES" / "messages.mo"
        
        if mo_file.exists():
            self._load_mo_file(mo_file)
    
    def _load_mo_file(self, filepath: Path) -> None:
        """
        Load translations from a .mo file.
        
        .mo files are compiled from .po files using msgfmt.
        This is a simplified implementation that works with JSON fallback.
        """
        try:
            import struct
            
            with open(filepath, 'rb') as f:
                # Read .mo file header
                magic = f.read(4)
                if magic == b'\x95\x04\x12\xde':
                    # Big endian
                    fmt = '>IIIIII'
                elif magic == b'\xde\x12\x04\x95':
                    # Little endian
                    fmt = '<IIIIII'
                else:
                    return  # Invalid .mo file
                
                # Read header fields
                (major, minor, num_strings, orig_offset,
                 trans_offset, hash_size) = struct.unpack(fmt, f.read(24))
                
                # Read string pairs
                for i in range(num_strings):
                    # Original string
                    f.seek(orig_offset + i * 8)
                    length, offset = struct.unpack(fmt[:2] + 'II', f.read(8))
                    f.seek(offset)
                    orig = f.read(length).decode('utf-8')
                    
                    # Translation string
                    f.seek(trans_offset + i * 8)
                    length, offset = struct.unpack(fmt[:2] + 'II', f.read(8))
                    f.seek(offset)
                    trans = f.read(length).decode('utf-8')
                    
                    # Handle plural forms
                    if '\x00' in orig:
                        # Plural form
                        singular, plural = orig.split('\x00')
                        translations = trans.split('\x00')
                        self._plural_catalog[singular] = {
                            i: t for i, t in enumerate(translations)
                        }
                    else:
                        self._catalog[orig] = trans
        
        except Exception:
            # Fallback to JSON translation file
            json_file = filepath.with_suffix('.json')
            if json_file.exists():
                import json
                with open(json_file, 'r', encoding='utf-8') as f:
                    self._catalog = json.load(f)
    
    def gettext(self, message: str) -> str:
        """Get translation for a message."""
        return self._catalog.get(message, message)
    
    def ngettext(self, singular: str, plural: str, count: int) -> str:
        """Get translation for a message with plural forms."""
        if singular in self._plural_catalog:
            plural_trans = self._plural_catalog[singular]
            # Simple plural formula: n == 1 ? 0 : 1
            idx = 0 if count == 1 else 1
            return plural_trans.get(idx, singular if count == 1 else plural)
        
        return singular if count == 1 else plural
    
    def pgettext(self, context: str, message: str) -> str:
        """Get translation with context."""
        key = f"{context}\x04{message}"
        return self._catalog.get(key, message)
    
    def npgettext(
        self,
        context: str,
        singular: str,
        plural: str,
        count: int,
    ) -> str:
        """Get translation with context and plural forms."""
        key = f"{context}\x04{singular}"
        if key in self._plural_catalog:
            plural_trans = self._plural_catalog[key]
            idx = 0 if count == 1 else 1
            return plural_trans.get(idx, singular if count == 1 else plural)
        
        return singular if count == 1 else plural


class NullTranslation(Translation):
    """
    Null translation that returns messages unchanged.
    
    Used when no translation is available for the current language.
    """
    
    def __init__(self):
        super().__init__('en')
    
    def gettext(self, message: str) -> str:
        return message
    
    def ngettext(self, singular: str, plural: str, count: int) -> str:
        return singular if count == 1 else plural


# Cache for loaded translations
_translations: dict[str, Translation] = {}


def get_translation(language: str) -> Translation:
    """
    Get or create a translation object for a language.
    
    Args:
        language: Language code
    
    Returns:
        Translation object
    """
    if language in _translations:
        return _translations[language]
    
    # Try to find translation directory
    from faststack.config import settings
    
    translation_dir = None
    locale_paths = getattr(settings, 'LOCALE_PATHS', [])
    
    for path in locale_paths:
        p = Path(path)
        if (p / language).exists():
            translation_dir = p
            break
    
    if translation_dir:
        translation = Translation(language, translation_dir)
    else:
        translation = NullTranslation()
    
    _translations[language] = translation
    return translation


def get_language() -> str | None:
    """
    Get the current active language.
    
    Returns:
        Language code or None if not set
    """
    return getattr(_active, 'language', None)


def activate(language: str) -> None:
    """
    Activate a language for the current thread.
    
    Args:
        language: Language code to activate
    """
    _active.language = language


def deactivate() -> None:
    """Deactivate the current language (revert to default)."""
    if hasattr(_active, 'language'):
        del _active.language


def gettext(message: str) -> str:
    """
    Translate a message.
    
    Example:
        message = gettext("Welcome to our site")
    
    Args:
        message: Message to translate
    
    Returns:
        Translated message (or original if no translation)
    """
    language = get_language()
    if language:
        return get_translation(language).gettext(message)
    return message


def ngettext(singular: str, plural: str, count: int) -> str:
    """
    Translate a message with plural forms.
    
    Example:
        count = len(items)
        message = ngettext(
            "You have %(count)d message",
            "You have %(count)d messages",
            count
        ) % {"count": count}
    
    Args:
        singular: Singular form of message
        plural: Plural form of message
        count: Count to determine which form to use
    
    Returns:
        Translated message with correct plural form
    """
    language = get_language()
    if language:
        return get_translation(language).ngettext(singular, plural, count)
    return singular if count == 1 else plural


def pgettext(context: str, message: str) -> str:
    """
    Translate a message with context.
    
    Context helps distinguish between different uses of the same word.
    
    Example:
        # May is a month name
        month = pgettext("month name", "May")
        # May is permission
        permission = pgettext("permission", "May")
    
    Args:
        context: Context string
        message: Message to translate
    
    Returns:
        Translated message
    """
    language = get_language()
    if language:
        return get_translation(language).pgettext(context, message)
    return message


def npgettext(
    context: str,
    singular: str,
    plural: str,
    count: int,
) -> str:
    """
    Translate a message with context and plural forms.
    
    Args:
        context: Context string
        singular: Singular form
        plural: Plural form
        count: Count for plural selection
    
    Returns:
        Translated message
    """
    language = get_language()
    if language:
        return get_translation(language).npgettext(context, singular, plural, count)
    return singular if count == 1 else plural


def gettext_lazy(message: str) -> str:
    """
    Lazy translation that defers until the message is actually used.
    
    Useful for translations in module-level constants.
    
    Args:
        message: Message to translate
    
    Returns:
        Lazy string that translates when str() is called
    """
    class LazyString:
        def __init__(self, msg):
            self._msg = msg
        
        def __str__(self):
            return gettext(self._msg)
        
        def __repr__(self):
            return repr(str(self))
        
        def __mod__(self, other):
            return str(self) % other
        
        def format(self, *args, **kwargs):
            return str(self).format(*args, **kwargs)
    
    return LazyString(message)


@lru_cache(maxsize=100)
def get_language_info(language: str) -> dict[str, Any]:
    """
    Get information about a language.
    
    Args:
        language: Language code
    
    Returns:
        Dict with language info:
            - code: Language code
            - name: Language name in English
            - name_local: Language name in that language
            - bidi: True if right-to-left language
    """
    # Common language info
    language_data = {
        'en': {'code': 'en', 'name': 'English', 'name_local': 'English', 'bidi': False},
        'de': {'code': 'de', 'name': 'German', 'name_local': 'Deutsch', 'bidi': False},
        'fr': {'code': 'fr', 'name': 'French', 'name_local': 'Français', 'bidi': False},
        'es': {'code': 'es', 'name': 'Spanish', 'name_local': 'Español', 'bidi': False},
        'it': {'code': 'it', 'name': 'Italian', 'name_local': 'Italiano', 'bidi': False},
        'pt': {'code': 'pt', 'name': 'Portuguese', 'name_local': 'Português', 'bidi': False},
        'ru': {'code': 'ru', 'name': 'Russian', 'name_local': 'Русский', 'bidi': False},
        'zh': {'code': 'zh', 'name': 'Chinese', 'name_local': '中文', 'bidi': False},
        'zh_CN': {'code': 'zh_CN', 'name': 'Chinese (Simplified)', 'name_local': '简体中文', 'bidi': False},
        'zh_TW': {'code': 'zh_TW', 'name': 'Chinese (Traditional)', 'name_local': '繁體中文', 'bidi': False},
        'ja': {'code': 'ja', 'name': 'Japanese', 'name_local': '日本語', 'bidi': False},
        'ko': {'code': 'ko', 'name': 'Korean', 'name_local': '한국어', 'bidi': False},
        'ar': {'code': 'ar', 'name': 'Arabic', 'name_local': 'العربية', 'bidi': True},
        'he': {'code': 'he', 'name': 'Hebrew', 'name_local': 'עברית', 'bidi': True},
        'fa': {'code': 'fa', 'name': 'Persian', 'name_local': 'فارسی', 'bidi': True},
        'nl': {'code': 'nl', 'name': 'Dutch', 'name_local': 'Nederlands', 'bidi': False},
        'pl': {'code': 'pl', 'name': 'Polish', 'name_local': 'Polski', 'bidi': False},
        'tr': {'code': 'tr', 'name': 'Turkish', 'name_local': 'Türkçe', 'bidi': False},
        'vi': {'code': 'vi', 'name': 'Vietnamese', 'name_local': 'Tiếng Việt', 'bidi': False},
        'th': {'code': 'th', 'name': 'Thai', 'name_local': 'ไทย', 'bidi': False},
        'id': {'code': 'id', 'name': 'Indonesian', 'name_local': 'Bahasa Indonesia', 'bidi': False},
        'hi': {'code': 'hi', 'name': 'Hindi', 'name_local': 'हिन्दी', 'bidi': False},
        'uk': {'code': 'uk', 'name': 'Ukrainian', 'name_local': 'Українська', 'bidi': False},
        'cs': {'code': 'cs', 'name': 'Czech', 'name_local': 'Čeština', 'bidi': False},
        'sv': {'code': 'sv', 'name': 'Swedish', 'name_local': 'Svenska', 'bidi': False},
        'da': {'code': 'da', 'name': 'Danish', 'name_local': 'Dansk', 'bidi': False},
        'no': {'code': 'no', 'name': 'Norwegian', 'name_local': 'Norsk', 'bidi': False},
        'fi': {'code': 'fi', 'name': 'Finnish', 'name_local': 'Suomi', 'bidi': False},
    }
    
    if language in language_data:
        return language_data[language].copy()
    
    # Generate basic info for unknown languages
    code = language.split('_')[0]
    return {
        'code': language,
        'name': language.upper(),
        'name_local': language.upper(),
        'bidi': code in ('ar', 'he', 'fa', 'ur'),
    }
