"""
FastStack Multiple Database Support - Database routing.
"""

from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


class DatabaseRouter(ABC):
    """Base class for database routers."""

    @abstractmethod
    def db_for_read(self, model: Type, **hints) -> Optional[str]:
        """Suggest database for read operations."""
        pass

    @abstractmethod
    def db_for_write(self, model: Type, **hints) -> Optional[str]:
        """Suggest database for write operations."""
        pass

    def allow_relation(self, obj1: Any, obj2: Any, **hints) -> Optional[bool]:
        """Determine if relation is allowed."""
        return None

    def allow_migrate(self, db: str, app_label: str, model_name: str = None, **hints) -> Optional[bool]:
        """Determine if migration should run."""
        return None


class PrimaryReplicaRouter(DatabaseRouter):
    """Router that sends reads to replicas and writes to primary."""

    def __init__(self, primary: str = 'default', replicas: List[str] = None):
        self.primary = primary
        self.replicas = replicas or []
        self._current_replica = 0

    def db_for_read(self, model: Type, **hints) -> Optional[str]:
        if not self.replicas:
            return self.primary
        replica = self.replicas[self._current_replica % len(self.replicas)]
        self._current_replica += 1
        return replica

    def db_for_write(self, model: Type, **hints) -> Optional[str]:
        return self.primary


class AppRouter(DatabaseRouter):
    """Router that routes by app label."""

    def __init__(self, app_mapping: Dict[str, str], default: str = 'default'):
        self.app_mapping = app_mapping
        self.default = default

    def db_for_read(self, model: Type, **hints) -> Optional[str]:
        app_label = model.__module__.split('.')[0] if hasattr(model, '__module__') else ''
        return self.app_mapping.get(app_label)

    def db_for_write(self, model: Type, **hints) -> Optional[str]:
        app_label = model.__module__.split('.')[0] if hasattr(model, '__module__') else ''
        return self.app_mapping.get(app_label)


class CompositeRouter(DatabaseRouter):
    """Router that tries multiple routers in order."""

    def __init__(self, routers: List[DatabaseRouter]):
        self.routers = routers

    def db_for_read(self, model: Type, **hints) -> Optional[str]:
        for router in self.routers:
            db = router.db_for_read(model, **hints)
            if db is not None:
                return db
        return None

    def db_for_write(self, model: Type, **hints) -> Optional[str]:
        for router in self.routers:
            db = router.db_for_write(model, **hints)
            if db is not None:
                return db
        return None


class using:
    """Context manager for selecting database."""

    _stack: List[str] = []

    def __init__(self, alias: str):
        self.alias = alias

    def __enter__(self):
        using._stack.append(self.alias)
        return self

    def __exit__(self, *args):
        if using._stack and using._stack[-1] == self.alias:
            using._stack.pop()

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, *args):
        self.__exit__(*args)

    @classmethod
    def get_current_db(cls) -> Optional[str]:
        return cls._stack[-1] if cls._stack else None
