"""
Lazy Objects - Deferred evaluation.

Example:
    from faststack.utils import LazyObject, lazy

    # Lazy settings
    settings = LazySettings('myapp.settings')

    # Lazy function evaluation
    expensive_value = lazy(expensive_function)()

    # First access evaluates
    print(settings.DEBUG)  # Settings loaded here
"""

from typing import Any, Callable, Optional, Type, Union
import importlib
import functools


class LazyObject:
    """
    Wrapper for lazy evaluation of objects.

    The wrapped object is only created when first accessed.

    Example:
        lazy_user = LazyObject(lambda: get_current_user())
        user = lazy_user.get()  # Object created here
    """

    # Sentinel for unset value
    _unset = object()

    def __init__(self, factory: Callable[[], Any] = None):
        """
        Initialize LazyObject.

        Args:
            factory: Callable that creates the wrapped object
        """
        self._factory = factory
        self._wrapped = self._unset

    def __repr__(self) -> str:
        if self._wrapped is self._unset:
            return f"<LazyObject (not evaluated)>"
        return f"<LazyObject: {self._wrapped!r}>"

    def __str__(self) -> str:
        return str(self._get_wrapped())

    def _get_wrapped(self) -> Any:
        """Get the wrapped object, creating it if necessary."""
        if self._wrapped is self._unset:
            self._wrapped = self._factory()
        return self._wrapped

    def __getattr__(self, name: str) -> Any:
        # Don't trigger evaluation for private attributes
        if name.startswith('_'):
            raise AttributeError(name)
        return getattr(self._get_wrapped(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ('_factory', '_wrapped'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._get_wrapped(), name, value)

    def __delattr__(self, name: str) -> None:
        delattr(self._get_wrapped(), name)

    def __bool__(self) -> bool:
        return bool(self._get_wrapped())

    def __len__(self) -> int:
        return len(self._get_wrapped())

    def __iter__(self):
        return iter(self._get_wrapped())

    def __getitem__(self, key):
        return self._get_wrapped()[key]

    def __setitem__(self, key, value):
        self._get_wrapped()[key] = value

    def __delitem__(self, key):
        del self._get_wrapped()[key]

    def __contains__(self, item):
        return item in self._get_wrapped()

    def __eq__(self, other):
        return self._get_wrapped() == other

    def __hash__(self):
        return hash(self._get_wrapped())

    # Proxy all special methods
    __add__ = lambda self, other: self._get_wrapped() + other
    __radd__ = lambda self, other: other + self._get_wrapped()
    __sub__ = lambda self, other: self._get_wrapped() - other
    __rsub__ = lambda self, other: other - self._get_wrapped()
    __mul__ = lambda self, other: self._get_wrapped() * other
    __rmul__ = lambda self, other: other * self._get_wrapped()
    __truediv__ = lambda self, other: self._get_wrapped() / other
    __rtruediv__ = lambda self, other: other / self._get_wrapped()
    __floordiv__ = lambda self, other: self._get_wrapped() // other
    __rfloordiv__ = lambda self, other: other // self._get_wrapped()
    __mod__ = lambda self, other: self._get_wrapped() % other
    __rmod__ = lambda self, other: other % self._get_wrapped()
    __pow__ = lambda self, other: self._get_wrapped() ** other
    __rpow__ = lambda self, other: other ** self._get_wrapped()
    __lshift__ = lambda self, other: self._get_wrapped() << other
    __rlshift__ = lambda self, other: other << self._get_wrapped()
    __rshift__ = lambda self, other: self._get_wrapped() >> other
    __rrshift__ = lambda self, other: other >> self._get_wrapped()
    __and__ = lambda self, other: self._get_wrapped() & other
    __rand__ = lambda self, other: other & self._get_wrapped()
    __xor__ = lambda self, other: self._get_wrapped() ^ other
    __rxor__ = lambda self, other: other ^ self._get_wrapped()
    __or__ = lambda self, other: self._get_wrapped() | other
    __ror__ = lambda self, other: other | self._get_wrapped()
    __neg__ = lambda self: -self._get_wrapped()
    __pos__ = lambda self: +self._get_wrapped()
    __abs__ = lambda self: abs(self._get_wrapped())
    __invert__ = lambda self: ~self._get_wrapped()
    __call__ = lambda self, *args, **kwargs: self._get_wrapped()(*args, **kwargs)


class LazySettings(LazyObject):
    """
    Lazy settings loader.

    Settings are loaded from a module when first accessed.

    Example:
        settings = LazySettings('myapp.settings')
        print(settings.DEBUG)  # Settings loaded here
    """

    def __init__(self, settings_module: str = None):
        """
        Initialize LazySettings.

        Args:
            settings_module: Module path to load settings from
        """
        self._settings_module = settings_module
        super().__init__(self._load_settings)

    def _load_settings(self) -> Any:
        """Load settings module and create settings object."""
        if self._settings_module is None:
            # Return empty settings
            return type('Settings', (), {'__dict__': {}})()

        try:
            module = importlib.import_module(self._settings_module)
            return module
        except ImportError:
            # Return empty settings
            return type('Settings', (), {'__dict__': {}})()

    def configure(self, **settings):
        """
        Configure settings manually.

        Args:
            **settings: Settings to set
        """
        wrapped = self._get_wrapped()
        for key, value in settings.items():
            setattr(wrapped, key, value)

    @property
    def configured(self) -> bool:
        """Check if settings have been configured."""
        return self._wrapped is not self._unset


def lazy(func: Callable = None, *, resultclass: type = None):
    """
    Decorator for lazy function evaluation.

    Args:
        func: Function to wrap
        resultclass: Expected result class

    Returns:
        Lazy wrapper

    Example:
        @lazy
        def expensive_function():
            return some_expensive_computation()

        result = expensive_function()  # Not evaluated yet
        value = result.get()  # Evaluated here
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            factory = lambda: f(*args, **kwargs)
            return LazyObject(factory)
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


class SimpleLazyObject:
    """
    Simplified lazy object that stores factory and args separately.

    Useful for pickling.

    Example:
        user = SimpleLazyObject(get_user, request)
        # ... later
        actual_user = user.get()
    """

    def __init__(self, factory: Callable, *args, **kwargs):
        self._factory = factory
        self._args = args
        self._kwargs = kwargs
        self._wrapped = None
        self._evaluated = False

    def __repr__(self) -> str:
        if self._evaluated:
            return repr(self._wrapped)
        return f"<SimpleLazyObject>"

    def _get(self) -> Any:
        if not self._evaluated:
            self._wrapped = self._factory(*self._args, **self._kwargs)
            self._evaluated = True
        return self._wrapped

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ('_factory', '_args', '_kwargs', '_wrapped', '_evaluated'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._get(), name, value)

    def __bool__(self) -> bool:
        return bool(self._get())


def keep_lazy(*resultclasses):
    """
    Decorator that keeps function result lazy.

    Args:
        *resultclasses: Expected result classes

    Example:
        @keep_lazy(str)
        def lazy_upper(s):
            return s.upper()

        lazy_str = LazyObject(lambda: 'hello')
        result = lazy_upper(lazy_str)  # Still lazy
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if any argument is lazy
            has_lazy = any(isinstance(arg, LazyObject) for arg in args)
            has_lazy = has_lazy or any(isinstance(v, LazyObject) for v in kwargs.values())

            if has_lazy:
                # Return lazy result
                def factory():
                    evaluated_args = [
                        arg._get_wrapped() if isinstance(arg, LazyObject) else arg
                        for arg in args
                    ]
                    evaluated_kwargs = {
                        k: v._get_wrapped() if isinstance(v, LazyObject) else v
                        for k, v in kwargs.items()
                    }
                    return func(*evaluated_args, **evaluated_kwargs)
                return LazyObject(factory)

            return func(*args, **kwargs)
        return wrapper
    return decorator
