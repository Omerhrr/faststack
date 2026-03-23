"""
FastStack Messages Constants

Defines message levels and default tags for the messages framework.
Compatible with Django's messages framework levels.
"""

from typing import Final

# Message levels (matching Django's levels)
DEBUG: Final[int] = 10
INFO: Final[int] = 20
SUCCESS: Final[int] = 25
WARNING: Final[int] = 30
ERROR: Final[int] = 40

# Default level tags for CSS styling
DEFAULT_TAGS: Final[dict[int, str]] = {
    DEBUG: "debug",
    INFO: "info",
    SUCCESS: "success",
    WARNING: "warning",
    ERROR: "error",
}

# Default level names
DEFAULT_LEVELS: Final[dict[str, int]] = {
    "DEBUG": DEBUG,
    "INFO": INFO,
    "SUCCESS": SUCCESS,
    "WARNING": WARNING,
    "ERROR": ERROR,
}

# Session key for storing messages
MESSAGE_SESSION_KEY: Final[str] = "_messages"

# Cookie name for storing messages
MESSAGE_COOKIE_NAME: Final[str] = "messages"

# Default message lifetime in seconds (for cookie storage)
DEFAULT_MESSAGE_LIFETIME: Final[int] = 3600  # 1 hour

# Maximum cookie size (4KB minus some overhead)
MAX_COOKIE_SIZE: Final[int] = 3800
