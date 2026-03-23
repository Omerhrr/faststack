"""
Session storage backends.
"""

from typing import Any, Callable, Dict, Optional, Union
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import json
import base64
import hashlib
import secrets
import os
import pickle
import time

# Try to import Redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class SessionBase(ABC):
    """
    Base class for session storage.
    """

    # Session cookie name
    session_cookie_name = 'sessionid'

    # Session cookie age (in seconds)
    session_cookie_age = 60 * 60 * 24 * 7 * 2  # 2 weeks

    # Session cookie domain
    session_cookie_domain = None

    # Session cookie path
    session_cookie_path = '/'

    # Session cookie secure
    session_cookie_secure = False

    # Session cookie httponly
    session_cookie_httponly = True

    # Session cookie samesite
    session_cookie_samesite = 'Lax'

    def __init__(
        self,
        session_key: str = None,
        secret_key: str = None,
        **kwargs
    ):
        self._session_key = session_key
        self._session_cache: Dict[str, Any] = {}
        self._modified = False
        self._accessed = False
        self.secret_key = secret_key or secrets.token_hex(32)

    def __contains__(self, key: str) -> bool:
        return key in self._session()

    def __getitem__(self, key: str) -> Any:
        return self._session()[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._session()[key] = value
        self._modified = True

    def __delitem__(self, key: str) -> None:
        del self._session()[key]
        self._modified = True

    def __len__(self) -> int:
        return len(self._session())

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.session_key or 'new'}>"

    def _session(self) -> Dict[str, Any]:
        """Get the session dictionary (lazy loaded)."""
        if not self._session_cache:
            self._session_cache = self.load() or {}
            self._accessed = True
        return self._session_cache

    @property
    def session_key(self) -> Optional[str]:
        """Get the session key."""
        if not self._session_key:
            self._session_key = self.generate_session_key()
        return self._session_key

    @property
    def modified(self) -> bool:
        """Check if session has been modified."""
        return self._modified

    @modified.setter
    def modified(self, value: bool) -> None:
        self._modified = value

    @property
    def accessed(self) -> bool:
        """Check if session has been accessed."""
        return self._accessed

    @staticmethod
    def generate_session_key() -> str:
        """Generate a random session key."""
        return secrets.token_hex(20)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a session value."""
        return self._session().get(key, default)

    def pop(self, key: str, default: Any = None) -> Any:
        """Remove and return a session value."""
        value = self._session().pop(key, default)
        self._modified = True
        return value

    def setdefault(self, key: str, default: Any = None) -> Any:
        """Set a value if key doesn't exist."""
        if key not in self._session():
            self[key] = default
            self._modified = True
        return self[key]

    def update(self, dict_: Dict[str, Any]) -> None:
        """Update session with multiple values."""
        self._session().update(dict_)
        self._modified = True

    def clear(self) -> None:
        """Clear all session data."""
        self._session_cache = {}
        self._modified = True

    def keys(self) -> list:
        """Get all session keys."""
        return list(self._session().keys())

    def values(self) -> list:
        """Get all session values."""
        return list(self._session().values())

    def items(self) -> list:
        """Get all session items."""
        return list(self._session().items())

    def encode(self, session_dict: Dict[str, Any]) -> str:
        """Encode session data for storage."""
        data = json.dumps(session_dict, default=str)
        encoded = base64.urlsafe_b64encode(data.encode()).decode()

        # Add signature
        signature = self._sign(encoded)
        return f"{encoded}.{signature}"

    def decode(self, session_data: str) -> Optional[Dict[str, Any]]:
        """Decode session data from storage."""
        try:
            encoded, signature = session_data.rsplit('.', 1)

            # Verify signature
            if not secrets.compare_digest(signature, self._sign(encoded)):
                return None

            data = base64.urlsafe_b64decode(encoded.encode()).decode()
            return json.loads(data)
        except (ValueError, json.JSONDecodeError):
            return None

    def _sign(self, data: str) -> str:
        """Sign data with secret key."""
        return hashlib.sha256((data + self.secret_key).encode()).hexdigest()[:32]

    # Abstract methods to be implemented by subclasses

    @abstractmethod
    def load(self) -> Optional[Dict[str, Any]]:
        """Load session data from storage."""
        pass

    @abstractmethod
    def save(self, must_create: bool = False) -> None:
        """Save session data to storage."""
        pass

    @abstractmethod
    def delete(self, session_key: str = None) -> None:
        """Delete session from storage."""
        pass

    @abstractmethod
    def exists(self, session_key: str) -> bool:
        """Check if session exists in storage."""
        pass

    def cycle_key(self) -> None:
        """Generate a new session key while keeping data."""
        data = dict(self._session())
        self.delete()
        self._session_key = self.generate_session_key()
        self._session_cache = data
        self.save(must_create=True)

    def flush(self) -> None:
        """Delete session and create a new empty one."""
        self.delete()
        self._session_key = None
        self._session_cache = {}
        self._modified = False


class SessionStore(SessionBase):
    """
    In-memory session store (for development/testing only).
    """

    _sessions: Dict[str, Dict[str, Any]] = {}

    def load(self) -> Optional[Dict[str, Any]]:
        return self._sessions.get(self.session_key)

    def save(self, must_create: bool = False) -> None:
        if must_create and self.exists(self.session_key):
            raise ValueError("Session already exists")

        self._sessions[self.session_key] = dict(self._session())

    def delete(self, session_key: str = None) -> None:
        key = session_key or self.session_key
        self._sessions.pop(key, None)

    def exists(self, session_key: str) -> bool:
        return session_key in self._sessions


class DatabaseSessionStore(SessionBase):
    """
    Database-backed session store.

    Stores sessions in a database table.
    """

    def __init__(
        self,
        session_key: str = None,
        database: Any = None,
        **kwargs
    ):
        super().__init__(session_key, **kwargs)
        self.database = database

    def load(self) -> Optional[Dict[str, Any]]:
        if not self.database or not self._session_key:
            return {}

        from .models import Session

        # This would need to be async
        # For now, return empty dict
        return {}

    async def aload(self) -> Optional[Dict[str, Any]]:
        """Async load session data."""
        if not self.database or not self._session_key:
            return {}

        from .models import Session
        session = await Session.get(self._session_key, self.database)

        if session and session.expire_date > datetime.utcnow():
            return self.decode(session.session_data) or {}

        return {}

    def save(self, must_create: bool = False) -> None:
        # Sync version - placeholder
        pass

    async def asave(self, must_create: bool = False) -> None:
        """Async save session data."""
        if not self.database:
            return

        from .models import Session

        session = Session(
            session_key=self.session_key,
            session_data=self.encode(self._session()),
            expire_date=datetime.utcnow() + timedelta(seconds=self.session_cookie_age)
        )
        await session.save(self.database)

    def delete(self, session_key: str = None) -> None:
        pass

    async def adelete(self, session_key: str = None) -> None:
        """Async delete session."""
        if not self.database:
            return

        from .models import Session
        key = session_key or self.session_key
        session = await Session.get(key, self.database)
        if session:
            await session.delete(self.database)

    def exists(self, session_key: str) -> bool:
        return False

    async def aexists(self, session_key: str) -> bool:
        """Async check if session exists."""
        if not self.database:
            return False

        from .models import Session
        return await Session.exists(session_key, self.database)


class RedisSessionStore(SessionBase):
    """
    Redis-backed session store.

    Stores sessions in Redis with automatic expiration.
    """

    def __init__(
        self,
        session_key: str = None,
        redis_url: str = 'redis://localhost:6379/0',
        prefix: str = 'session:',
        **kwargs
    ):
        super().__init__(session_key, **kwargs)
        self.redis_url = redis_url
        self.prefix = prefix
        self._redis = None

    async def _get_redis(self):
        """Get Redis connection."""
        if self._redis is None and REDIS_AVAILABLE:
            self._redis = await redis.from_url(self.redis_url)
        return self._redis

    def load(self) -> Optional[Dict[str, Any]]:
        return {}

    async def aload(self) -> Optional[Dict[str, Any]]:
        """Async load session data."""
        if not self._session_key:
            return {}

        client = await self._get_redis()
        if not client:
            return {}

        data = await client.get(f"{self.prefix}{self._session_key}")
        if data:
            return self.decode(data.decode())
        return {}

    def save(self, must_create: bool = False) -> None:
        pass

    async def asave(self, must_create: bool = False) -> None:
        """Async save session data."""
        client = await self._get_redis()
        if not client:
            return

        data = self.encode(self._session())
        key = f"{self.prefix}{self.session_key}"

        await client.setex(
            key,
            self.session_cookie_age,
            data
        )

    def delete(self, session_key: str = None) -> None:
        pass

    async def adelete(self, session_key: str = None) -> None:
        """Async delete session."""
        client = await self._get_redis()
        if not client:
            return

        key = f"{self.prefix}{session_key or self.session_key}"
        await client.delete(key)

    def exists(self, session_key: str) -> bool:
        return False

    async def aexists(self, session_key: str) -> bool:
        """Async check if session exists."""
        client = await self._get_redis()
        if not client:
            return False

        key = f"{self.prefix}{session_key}"
        return await client.exists(key) > 0


class CookieSessionStore(SessionBase):
    """
    Cookie-backed session store.

    Stores entire session in a signed cookie.
    Limited to ~4KB total size.
    """

    def __init__(
        self,
        session_key: str = None,
        request_cookies: Dict[str, str] = None,
        **kwargs
    ):
        super().__init__(session_key, **kwargs)
        self.request_cookies = request_cookies or {}

    def load(self) -> Optional[Dict[str, Any]]:
        cookie_value = self.request_cookies.get(self.session_cookie_name, '')
        if cookie_value:
            return self.decode(cookie_value)
        return {}

    def save(self, must_create: bool = False) -> None:
        # Cookie is saved in response, not here
        pass

    def delete(self, session_key: str = None) -> None:
        # Cookie is deleted by setting empty value
        self._session_cache = {}

    def exists(self, session_key: str) -> bool:
        return False  # Cookies are stateless

    def get_cookie_value(self) -> str:
        """Get the value to set in the session cookie."""
        return self.encode(self._session())


class FileSessionStore(SessionBase):
    """
    File-backed session store.

    Stores sessions as files in a directory.
    """

    def __init__(
        self,
        session_key: str = None,
        storage_path: str = '/tmp/sessions',
        **kwargs
    ):
        super().__init__(session_key, **kwargs)
        self.storage_path = storage_path

        # Ensure directory exists
        os.makedirs(storage_path, exist_ok=True)

    def _get_file_path(self, session_key: str) -> str:
        return os.path.join(self.storage_path, f"session_{session_key}")

    def load(self) -> Optional[Dict[str, Any]]:
        if not self._session_key:
            return {}

        file_path = self._get_file_path(self._session_key)

        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)

            # Check expiration
            if data.get('_expire_date', 0) < time.time():
                os.remove(file_path)
                return {}

            return data.get('_session_data', {})
        except (FileNotFoundError, pickle.PickleError):
            return {}

    def save(self, must_create: bool = False) -> None:
        file_path = self._get_file_path(self.session_key)

        data = {
            '_session_data': self._session(),
            '_expire_date': time.time() + self.session_cookie_age
        }

        with open(file_path, 'wb') as f:
            pickle.dump(data, f)

    def delete(self, session_key: str = None) -> None:
        key = session_key or self.session_key
        file_path = self._get_file_path(key)

        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass

    def exists(self, session_key: str) -> bool:
        return os.path.exists(self._get_file_path(session_key))


class CacheSessionStore(SessionBase):
    """
    Cache-backed session store.

    Uses FastStack's cache framework for session storage.
    """

    def __init__(
        self,
        session_key: str = None,
        cache: Any = None,
        cache_key_prefix: str = 'session:',
        **kwargs
    ):
        super().__init__(session_key, **kwargs)
        self.cache = cache
        self.cache_key_prefix = cache_key_prefix

    def _get_cache_key(self, session_key: str) -> str:
        return f"{self.cache_key_prefix}{session_key}"

    def load(self) -> Optional[Dict[str, Any]]:
        if not self._session_key or not self.cache:
            return {}

        cache_key = self._get_cache_key(self._session_key)
        data = self.cache.get(cache_key)

        if data:
            return self.decode(data)
        return {}

    def save(self, must_create: bool = False) -> None:
        if not self.cache:
            return

        cache_key = self._get_cache_key(self.session_key)
        data = self.encode(self._session())

        self.cache.set(cache_key, data, timeout=self.session_cookie_age)

    def delete(self, session_key: str = None) -> None:
        if not self.cache:
            return

        key = self._get_cache_key(session_key or self.session_key)
        self.cache.delete(key)

    def exists(self, session_key: str) -> bool:
        if not self.cache:
            return False

        return self.cache.get(self._get_cache_key(session_key)) is not None
