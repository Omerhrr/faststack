"""
Message level constants and tags.
"""

from enum import IntEnum


class Level(IntEnum):
    """Message severity levels."""

    # Debug messages (only shown in debug mode)
    DEBUG = 10

    # Informational messages
    INFO = 20

    # Success messages (after successful action)
    SUCCESS = 25

    # Warning messages (potential issues)
    WARNING = 30

    # Error messages (failed action)
    ERROR = 40


# Export constants for convenience
DEBUG = Level.DEBUG
INFO = Level.INFO
SUCCESS = Level.SUCCESS
WARNING = Level.WARNING
ERROR = Level.ERROR

# Mapping of level to tag (for CSS classes)
DEFAULT_TAGS = {
    DEBUG: 'debug',
    INFO: 'info',
    SUCCESS: 'success',
    WARNING: 'warning',
    ERROR: 'error',
}

# Human-readable level names
DEFAULT_LEVELS = {
    DEBUG: 'Debug',
    INFO: 'Info',
    SUCCESS: 'Success',
    WARNING: 'Warning',
    ERROR: 'Error',
}
