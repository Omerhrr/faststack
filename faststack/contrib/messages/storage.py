"""
FastStack Messages Storage Backends

Provides storage backends for the messages framework including:
- BaseStorage: Abstract base class
- SessionStorage: Store messages in session
- CookieStorage: Store messages in signed cookie
- FallbackStorage: Try cookie, fallback to session

Django-compatible but async-first design.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Iterator, Sequence

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from starlette.requests import Request
from starlette.responses import Response

from faststack.config import settings
from faststack.contrib.messages.constants import (
    DEBUG,
    DEFAULT_TAGS,
    ERROR,
    INFO,
    MESSAGE_COOKIE_NAME,
    MESSAGE_SESSION_KEY,
    SUCCESS,
    WARNING,
    DEFAULT_MESSAGE_LIFETIME,
    MAX_COOKIE_SIZE,
)


class Message:
    """
    Represents a single message.

    Attributes:
        level: Message level (DEBUG, INFO, SUCCESS, WARNING, ERROR)
        message: The message text
        extra_tags: Extra CSS tags for styling
        created_at: When the message was created

    Example:
        msg = Message(INFO, "Your profile has been updated.", extra_tags="alert-info")
        if msg.is_expired():
            # Handle expired message
            pass
    """

    def __init__(
        self,
        level: int,
        message: str,
        extra_tags: str = "",
        created_at: datetime | None = None,
    ):
        """
        Initialize a message.

        Args:
            level: Message level constant
            message: The message text
            extra_tags: Extra CSS tags
            created_at: Creation timestamp (defaults to now)
        """
        self.level = level
        self.message = message
        self.extra_tags = extra_tags
        self.created_at = created_at or datetime.utcnow()

    def __eq__(self, other: object) -> bool:
        """Check equality with another message."""
        if not isinstance(other, Message):
            return NotImplemented
        return (
            self.level == other.level
            and self.message == other.message
            and self.extra_tags == other.extra_tags
        )

    def __str__(self) -> str:
        """Return string representation."""
        return self.message

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"Message(level={self.level}, message={self.message!r}, extra_tags={self.extra_tags!r})"

    @property
    def tags(self) -> str:
        """
        Get all tags for this message.

        Combines the default tag for the level with extra tags.

        Returns:
            Space-separated string of CSS class names
        """
        tags = DEFAULT_TAGS.get(self.level, "")
        if self.extra_tags:
            tags = f"{tags} {self.extra_tags}" if tags else self.extra_tags
        return tags

    @property
    def level_tag(self) -> str:
        """
        Get the default tag for this message's level.

        Returns:
            Default CSS class for the message level
        """
        return DEFAULT_TAGS.get(self.level, "")

    def is_expired(self, lifetime: int | None = None) -> bool:
        """
        Check if the message has expired.

        Used by CookieStorage to determine if a message should be discarded.

        Args:
            lifetime: Maximum age in seconds (default: DEFAULT_MESSAGE_LIFETIME)

        Returns:
            True if the message has expired
        """
        if lifetime is None:
            lifetime = DEFAULT_MESSAGE_LIFETIME

        expiry_time = self.created_at + timedelta(seconds=lifetime)
        return datetime.utcnow() > expiry_time

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the message to a dictionary.

        Returns:
            Dictionary representation of the message
        """
        return {
            "level": self.level,
            "message": self.message,
            "extra_tags": self.extra_tags,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """
        Deserialize a message from a dictionary.

        Args:
            data: Dictionary with message data

        Returns:
            Message instance
        """
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = None

        return cls(
            level=data["level"],
            message=data["message"],
            extra_tags=data.get("extra_tags", ""),
            created_at=created_at,
        )


class BaseStorage(ABC):
    """
    Abstract base class for message storage backends.

    Subclasses must implement:
        - _get_messages(): Get messages from storage
        - _store_messages(): Store messages in storage
        - _get_level(): Get minimum message level
        - _set_level(): Set minimum message level
    """

    session_key = MESSAGE_SESSION_KEY

    def __init__(self, request: Request):
        """
        Initialize storage with a request object.

        Args:
            request: Starlette request object
        """
        self.request = request
        self._queued_messages: list[Message] = []

    def __len__(self) -> int:
        """Return the number of messages."""
        return len(self._get_messages()) + len(self._queued_messages)

    def __iter__(self) -> Iterator[Message]:
        """Iterate over all messages."""
        for msg in self._get_messages():
            yield msg
        for msg in self._queued_messages:
            yield msg

    def __contains__(self, item: Message | str) -> bool:
        """Check if a message is in storage."""
        messages = list(self)
        if isinstance(item, Message):
            return item in messages
        return any(item in msg.message for msg in messages)

    def add(
        self,
        level: int,
        message: str,
        extra_tags: str = "",
    ) -> None:
        """
        Add a message to the storage.

        The message is queued and will be stored when the response is processed.

        Args:
            level: Message level constant
            message: Message text
            extra_tags: Extra CSS tags
        """
        # Check if message level is above minimum
        if level < self.get_level():
            return

        msg = Message(level, message, extra_tags)
        self._queued_messages.append(msg)

    def get_messages(self) -> list[Message]:
        """
        Get all stored messages.

        Also marks messages as read by clearing stored messages.

        Returns:
            List of Message objects
        """
        messages = list(self._get_messages())
        # Also include queued messages
        messages.extend(self._queued_messages)
        return messages

    def update(self, response: Response) -> None:
        """
        Update storage after response.

        Called by middleware to persist queued messages.

        Args:
            response: Starlette response object
        """
        if self._queued_messages:
            existing = list(self._get_messages())
            existing.extend(self._queued_messages)
            self._store_messages(existing, response)
            self._queued_messages = []

    @abstractmethod
    def _get_messages(self) -> Sequence[Message]:
        """
        Get messages from storage.

        Returns:
            Sequence of stored messages
        """
        ...

    @abstractmethod
    def _store_messages(self, messages: list[Message], response: Response) -> None:
        """
        Store messages in storage.

        Args:
            messages: Messages to store
            response: Response object (for setting cookies)
        """
        ...

    def get_level(self) -> int:
        """
        Get the minimum message level.

        Returns:
            Minimum level (messages below this are not stored)
        """
        return self._get_level()

    def set_level(self, level: int | None) -> None:
        """
        Set the minimum message level.

        Args:
            level: New minimum level (None to use default)
        """
        self._set_level(level)

    @abstractmethod
    def _get_level(self) -> int:
        """Get minimum message level from storage."""
        ...

    @abstractmethod
    def _set_level(self, level: int | None) -> None:
        """Set minimum message level in storage."""
        ...


class SessionStorage(BaseStorage):
    """
    Store messages in the session.

    This is the default storage backend and works well with any session backend.
    Messages persist across requests until they are retrieved.

    Example:
        storage = SessionStorage(request)
        storage.add(INFO, "Hello, world!")
        # Messages are stored in request.session['_messages']
    """

    session_key = MESSAGE_SESSION_KEY
    level_session_key = "_messages_level"

    def _get_messages(self) -> Sequence[Message]:
        """Get messages from session."""
        data = self.request.session.get(self.session_key, [])
        messages = []
        for item in data:
            try:
                msg = Message.from_dict(item)
                messages.append(msg)
            except (KeyError, ValueError):
                # Skip malformed messages
                continue
        return messages

    def _store_messages(self, messages: list[Message], response: Response) -> None:
        """Store messages in session."""
        data = [msg.to_dict() for msg in messages]
        self.request.session[self.session_key] = data

    def _get_level(self) -> int:
        """Get minimum level from session."""
        return self.request.session.get(self.level_session_key, INFO)

    def _set_level(self, level: int | None) -> None:
        """Set minimum level in session."""
        if level is None:
            self.request.session.pop(self.level_session_key, None)
        else:
            self.request.session[self.level_session_key] = level


class CookieStorage(BaseStorage):
    """
    Store messages in signed cookies.

    Messages are stored client-side in a signed cookie. This avoids
    server-side storage but has size limitations (4KB max).

    Features:
        - No server-side storage required
        - Cryptographically signed (tamper-proof)
        - Auto-expires old messages
        - Limited to ~4KB total

    Example:
        storage = CookieStorage(request)
        storage.add(SUCCESS, "Settings saved!")
        # Messages stored in a signed cookie
    """

    cookie_name = MESSAGE_COOKIE_NAME
    level_cookie_name = "messages_level"
    max_age = DEFAULT_MESSAGE_LIFETIME

    def __init__(self, request: Request):
        """Initialize with request and set up serializer."""
        super().__init__(request)
        self.serializer = URLSafeTimedSerializer(
            settings.SECRET_KEY,
            salt="faststack.messages",
        )

    def _get_messages(self) -> Sequence[Message]:
        """Get messages from cookie."""
        cookie = self.request.cookies.get(self.cookie_name)
        if not cookie:
            return []

        try:
            data = self.serializer.loads(cookie, max_age=self.max_age)
        except (BadSignature, SignatureExpired):
            return []

        if not isinstance(data, list):
            return []

        messages = []
        for item in data:
            try:
                msg = Message.from_dict(item)
                # Filter out expired messages
                if not msg.is_expired(self.max_age):
                    messages.append(msg)
            except (KeyError, ValueError):
                continue

        return messages

    def _store_messages(self, messages: list[Message], response: Response) -> None:
        """Store messages in a signed cookie."""
        # Filter out expired messages
        valid_messages = [
            msg for msg in messages if not msg.is_expired(self.max_age)
        ]

        if not valid_messages:
            # Delete cookie if no messages
            response.delete_cookie(self.cookie_name)
            return

        data = [msg.to_dict() for msg in valid_messages]
        encoded = self.serializer.dumps(data)

        # Check cookie size
        if len(encoded) > MAX_COOKIE_SIZE:
            # Fall back to session storage if too large
            # This shouldn't happen in normal use
            raise ValueError(
                f"Message cookie too large ({len(encoded)} bytes). "
                "Use session storage or reduce message size."
            )

        response.set_cookie(
            key=self.cookie_name,
            value=encoded,
            max_age=self.max_age,
            httponly=True,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            secure=settings.SESSION_COOKIE_SECURE,
        )

    def _get_level(self) -> int:
        """Get minimum level from cookie."""
        cookie = self.request.cookies.get(self.level_cookie_name)
        if not cookie:
            return INFO

        try:
            level = int(cookie)
        except (ValueError, TypeError):
            return INFO

        return level

    def _set_level(self, level: int | None) -> None:
        """Set minimum level in cookie."""
        # Level is set via response, store for later
        self._level = level

    def update(self, response: Response) -> None:
        """Update cookies after response."""
        super().update(response)

        # Set level cookie if changed
        if hasattr(self, "_level"):
            if self._level is None:
                response.delete_cookie(self.level_cookie_name)
            else:
                response.set_cookie(
                    key=self.level_cookie_name,
                    value=str(self._level),
                    max_age=self.max_age,
                    httponly=True,
                    samesite=settings.SESSION_COOKIE_SAMESITE,
                    secure=settings.SESSION_COOKIE_SECURE,
                )


class FallbackStorage(BaseStorage):
    """
    Try cookie storage first, fallback to session storage.

    This storage tries to use CookieStorage for small message loads.
    If the cookie would be too large, it automatically falls back
    to SessionStorage.

    This is the recommended storage for most applications.

    Example:
        storage = FallbackStorage(request)
        storage.add(INFO, "Item added to cart")
        storage.add(SUCCESS, "Order placed successfully")
        # Uses cookie if small enough, session otherwise
    """

    def __init__(self, request: Request):
        """Initialize with both cookie and session storage."""
        super().__init__(request)
        self._cookie_storage = CookieStorage(request)
        self._session_storage = SessionStorage(request)
        self._storage: BaseStorage | None = None

    def _get_storage(self) -> BaseStorage:
        """
        Get the appropriate storage backend.

        Returns cookie storage if it has messages or no session messages.
        Returns session storage otherwise.

        Returns:
            Storage backend to use
        """
        if self._storage is not None:
            return self._storage

        # Check if we already have messages in either storage
        cookie_messages = self._cookie_storage._get_messages()
        session_messages = self._session_storage._get_messages()

        # Prefer whichever has existing messages
        if cookie_messages and not session_messages:
            self._storage = self._cookie_storage
        elif session_messages:
            self._storage = self._session_storage
        else:
            # Default to cookie for new messages
            self._storage = self._cookie_storage

        return self._storage

    def _get_messages(self) -> Sequence[Message]:
        """Get messages from active storage."""
        return self._get_storage()._get_messages()

    def _store_messages(self, messages: list[Message], response: Response) -> None:
        """Store messages, trying cookie first then session."""
        storage = self._get_storage()

        try:
            storage._store_messages(messages, response)
        except ValueError:
            # Cookie too large, fall back to session
            self._storage = self._session_storage
            self._session_storage._store_messages(messages, response)
            # Clear any existing cookie
            response.delete_cookie(CookieStorage.cookie_name)

    def _get_level(self) -> int:
        """Get minimum level from active storage."""
        return self._get_storage()._get_level()

    def _set_level(self, level: int | None) -> None:
        """Set minimum level in active storage."""
        self._get_storage()._set_level(level)

    def update(self, response: Response) -> None:
        """Update storage after response."""
        if self._queued_messages:
            existing = list(self._get_messages())
            existing.extend(self._queued_messages)
            self._store_messages(existing, response)
            self._queued_messages = []
