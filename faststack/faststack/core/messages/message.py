"""
Message data class.
"""

from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time

from .constants import DEFAULT_TAGS, Level


@dataclass
class Message:
    """
    A single message with metadata.

    Attributes:
        level: Message severity level (DEBUG, INFO, SUCCESS, WARNING, ERROR)
        message: The message text
        extra_tags: Additional CSS tags
        created_at: Unix timestamp when message was created
        _id: Unique message identifier
    """

    level: int
    message: str
    extra_tags: str = ''
    created_at: float = field(default_factory=time.time)
    _id: Optional[int] = None

    def __repr__(self) -> str:
        return f"Message(level={self.level}, message='{self.message}')"

    def __str__(self) -> str:
        return self.message

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Message):
            return False
        return (
            self.level == other.level
            and self.message == other.message
            and self.extra_tags == other.extra_tags
        )

    @property
    def tags(self) -> str:
        """
        Get CSS class tags for this message.

        Returns:
            Space-separated CSS class names (e.g., "success alert")
        """
        tags = [DEFAULT_TAGS.get(self.level, '')]

        if self.extra_tags:
            tags.append(self.extra_tags)

        return ' '.join(tag for tag in tags if tag)

    @property
    def level_tag(self) -> str:
        """
        Get primary level tag for this message.

        Returns:
            Primary CSS class name (e.g., "success")
        """
        return DEFAULT_TAGS.get(self.level, '')

    @property
    def is_debug(self) -> bool:
        """Check if this is a debug message."""
        return self.level == Level.DEBUG

    @property
    def is_info(self) -> bool:
        """Check if this is an info message."""
        return self.level == Level.INFO

    @property
    def is_success(self) -> bool:
        """Check if this is a success message."""
        return self.level == Level.SUCCESS

    @property
    def is_warning(self) -> bool:
        """Check if this is a warning message."""
        return self.level == Level.WARNING

    @property
    def is_error(self) -> bool:
        """Check if this is an error message."""
        return self.level == Level.ERROR

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'level': self.level,
            'message': self.message,
            'extra_tags': self.extra_tags,
            'created_at': self.created_at,
            'id': self._id,
            'tags': self.tags,
            'level_tag': self.level_tag,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        """Create from dictionary."""
        return cls(
            level=data['level'],
            message=data['message'],
            extra_tags=data.get('extra_tags', ''),
            created_at=data.get('created_at', time.time()),
            _id=data.get('id'),
        )
