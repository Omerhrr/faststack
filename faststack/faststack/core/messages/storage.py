"""
Message storage backends.
"""

from typing import Any, Dict, List, Optional, Iterator
from abc import ABC, abstractmethod
import json
import base64
import hashlib
import secrets

from .message import Message
from .constants import DEBUG, ERROR


class BaseStorage(ABC):
    """
    Abstract base class for message storage backends.
    """

    # Key used to store messages in storage
    session_key = '_messages'

    def __init__(self, request: Any = None):
        """
        Initialize storage.

        Args:
            request: The request object
        """
        self.request = request
        self._queued_messages: List[Message] = []
        self._loaded = False
        self._loaded_messages: List[Message] = []
        self._id_counter = 0

    def __iter__(self) -> Iterator[Message]:
        """Iterate over messages."""
        return iter(self._get_messages())

    def __len__(self) -> int:
        """Return number of messages."""
        return len(self._get_messages())

    def __bool__(self) -> bool:
        """Return True if there are messages."""
        return len(self) > 0

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {len(self)} messages>"

    def _get_next_id(self) -> int:
        """Get next message ID."""
        self._id_counter += 1
        return self._id_counter

    def _get_messages(self) -> List[Message]:
        """Get all messages (loaded + queued)."""
        if not self._loaded:
            self._loaded_messages = list(self._load())
            self._loaded = True
        return self._loaded_messages + self._queued_messages

    def add(
        self,
        level: int,
        message: str,
        extra_tags: str = '',
        fail_silently: bool = True
    ) -> Message:
        """
        Add a message.

        Args:
            level: Message level
            message: Message text
            extra_tags: Additional CSS tags
            fail_silently: Don't raise errors if message can't be added

        Returns:
            The created Message object
        """
        if not message:
            return None

        msg = Message(
            level=level,
            message=str(message),
            extra_tags=extra_tags,
            _id=self._get_next_id()
        )
        self._queued_messages.append(msg)
        return msg

    def update(self, response: Any = None) -> None:
        """
        Store messages for the next request.

        Called after processing a request to persist messages.

        Args:
            response: The response object
        """
        self._store(self._queued_messages, response)
        self._queued_messages = []

    def _prepare_messages(self, messages: List[Message]) -> List[dict]:
        """Prepare messages for serialization."""
        return [msg.to_dict() for msg in messages]

    def _decode_messages(self, data: List[dict]) -> List[Message]:
        """Decode serialized messages."""
        return [Message.from_dict(d) for d in data]

    @abstractmethod
    def _load(self) -> List[Message]:
        """Load messages from storage."""
        pass

    @abstractmethod
    def _store(self, messages: List[Message], response: Any = None) -> None:
        """Store messages to storage."""
        pass

    def clear(self) -> None:
        """Clear all messages."""
        self._loaded_messages = []
        self._queued_messages = []
        self._store([], None)


class CookieStorage(BaseStorage):
    """
    Store messages in signed cookies.

    Pros: No server-side storage required
    Cons: Limited size (~4KB), stored on client

    Example:
        storage = CookieStorage(request)
        storage.add(SUCCESS, "Saved successfully!")
        storage.update(response)
    """

    # Cookie name
    cookie_name = 'messages'

    # Max cookie size (leave room for other cookies)
    max_cookie_size = 4093

    # Secret key for signing
    secret_key: str = None

    def __init__(self, request: Any = None, secret_key: str = None):
        super().__init__(request)

        # Get or generate secret key
        if secret_key:
            self.secret_key = secret_key
        elif hasattr(request, 'app') and hasattr(request.app, 'secret_key'):
            self.secret_key = request.app.secret_key
        elif hasattr(request, 'state') and hasattr(request.state, 'secret_key'):
            self.secret_key = request.state.secret_key
        else:
            # Generate a key for this session
            self.secret_key = secrets.token_hex(32)

    def _hash(self, value: str) -> str:
        """Create a hash for signing."""
        return hashlib.sha256((value + self.secret_key).encode()).hexdigest()[:32]

    def _encode(self, messages: List[Message]) -> str:
        """Encode messages to cookie value."""
        data = self._prepare_messages(messages)
        json_str = json.dumps(data)
        encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
        signature = self._hash(encoded)
        return f"{encoded}:{signature}"

    def _decode(self, cookie_value: str) -> Optional[List[dict]]:
        """Decode messages from cookie value."""
        try:
            encoded, signature = cookie_value.rsplit(':', 1)

            # Verify signature
            if not secrets.compare_digest(signature, self._hash(encoded)):
                return None

            json_str = base64.urlsafe_b64decode(encoded.encode()).decode()
            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError):
            return None

    def _load(self) -> List[Message]:
        """Load messages from cookie."""
        if not self.request:
            return []

        # Get cookie value
        cookies = getattr(self.request, 'cookies', {})
        cookie_value = cookies.get(self.cookie_name, '')

        if not cookie_value:
            return []

        data = self._decode(cookie_value)
        if data is None:
            return []

        return self._decode_messages(data)

    def _store(self, messages: List[Message], response: Any = None) -> None:
        """Store messages in cookie."""
        if not response:
            return

        if not messages:
            # Delete cookie
            if hasattr(response, 'delete_cookie'):
                response.delete_cookie(self.cookie_name)
            return

        # Encode messages
        encoded = self._encode(messages)

        # Check size
        if len(encoded) > self.max_cookie_size:
            # Message too large, keep only last error
            error_messages = [m for m in messages if m.level >= ERROR]
            if error_messages:
                encoded = self._encode([error_messages[-1]])
            else:
                return

        # Set cookie
        if hasattr(response, 'set_cookie'):
            response.set_cookie(
                self.cookie_name,
                encoded,
                max_age=60 * 60 * 24 * 7,  # 1 week
                httponly=True,
                samesite='Lax'
            )


class SessionStorage(BaseStorage):
    """
    Store messages in session.

    Pros: No size limit, server-side storage
    Cons: Requires session middleware

    Example:
        storage = SessionStorage(request)
        storage.add(SUCCESS, "Saved successfully!")
        storage.update(response)
    """

    def _load(self) -> List[Message]:
        """Load messages from session."""
        if not self.request:
            return []

        session = getattr(self.request, 'session', None)
        if not session:
            return []

        data = session.get(self.session_key, [])
        return self._decode_messages(data)

    def _store(self, messages: List[Message], response: Any = None) -> None:
        """Store messages in session."""
        if not self.request:
            return

        session = getattr(self.request, 'session', None)
        if not session:
            return

        if messages:
            session[self.session_key] = self._prepare_messages(messages)
        else:
            session.pop(self.session_key, None)

        # Save session if needed
        if hasattr(session, 'save'):
            session.save()


class DatabaseStorage(BaseStorage):
    """
    Store messages in database.

    Useful for long-term message persistence or when you need
    to access messages across multiple devices.

    Example:
        storage = DatabaseStorage(request, user_id=user.id)
        storage.add(SUCCESS, "Saved successfully!")
    """

    def __init__(
        self,
        request: Any = None,
        user_id: Any = None,
        session_key: str = None
    ):
        super().__init__(request)
        self.user_id = user_id
        self.session_key = session_key or (getattr(request, 'session_key', None) if request else None)

    def _load(self) -> List[Message]:
        """Load messages from database."""
        # This would need to be implemented with actual DB queries
        # For now, return empty list
        return []

    def _store(self, messages: List[Message], response: Any = None) -> None:
        """Store messages in database."""
        # This would need to be implemented with actual DB queries
        pass


class FallbackStorage(BaseStorage):
    """
    Try multiple storage backends with fallback.

    Attempts storage in order: session -> cookie -> memory

    Example:
        storage = FallbackStorage(request)
        storage.add(SUCCESS, "Saved successfully!")
    """

    storage_classes = [SessionStorage, CookieStorage]

    def __init__(self, request: Any = None):
        super().__init__(request)
        self._storages = [cls(request) for cls in self.storage_classes]

    def _load(self) -> List[Message]:
        """Load from first available storage."""
        for storage in self._storages:
            messages = list(storage._load())
            if messages:
                return messages
        return []

    def _store(self, messages: List[Message], response: Any = None) -> None:
        """Store in first successful storage."""
        for storage in self._storages:
            try:
                storage._store(messages, response)
                return
            except Exception:
                continue


class MessageStorage:
    """
    High-level message storage API.

    Provides a simple interface for adding and retrieving messages.

    Example:
        storage = MessageStorage(request)
        storage.success("Profile updated!")
        storage.error("Something went wrong.")

        for message in storage:
            print(message)
    """

    def __init__(self, request: Any = None, backend: str = 'fallback'):
        """
        Initialize message storage.

        Args:
            request: The request object
            backend: Storage backend ('cookie', 'session', 'fallback')
        """
        self.request = request

        if backend == 'cookie':
            self._storage = CookieStorage(request)
        elif backend == 'session':
            self._storage = SessionStorage(request)
        else:
            self._storage = FallbackStorage(request)

    def __iter__(self):
        return iter(self._storage)

    def __len__(self):
        return len(self._storage)

    def __bool__(self):
        return bool(self._storage)

    def add(self, level: int, message: str, extra_tags: str = '') -> Message:
        """Add a message with the given level."""
        return self._storage.add(level, message, extra_tags)

    def debug(self, message: str, extra_tags: str = '') -> Message:
        """Add a debug message."""
        return self.add(DEBUG, message, extra_tags)

    def info(self, message: str, extra_tags: str = '') -> Message:
        """Add an info message."""
        return self.add(DEBUG, message, extra_tags)

    def success(self, message: str, extra_tags: str = '') -> Message:
        """Add a success message."""
        from .constants import SUCCESS
        return self.add(SUCCESS, message, extra_tags)

    def warning(self, message: str, extra_tags: str = '') -> Message:
        """Add a warning message."""
        from .constants import WARNING
        return self.add(WARNING, message, extra_tags)

    def error(self, message: str, extra_tags: str = '') -> Message:
        """Add an error message."""
        return self.add(ERROR, message, extra_tags)

    def update(self, response: Any = None) -> None:
        """Persist messages for next request."""
        self._storage.update(response)

    def clear(self) -> None:
        """Clear all messages."""
        self._storage.clear()

    def get_messages(self) -> List[Message]:
        """Get all messages as list."""
        return list(self._storage)

    def count(self, level: int = None) -> int:
        """Count messages, optionally filtered by level."""
        if level:
            return len([m for m in self._storage if m.level == level])
        return len(self._storage)
