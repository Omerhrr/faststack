"""
Functional Utilities - cached_property, classproperty, etc.

Example:
    from faststack.utils import cached_property, classproperty

    class MyClass:
        @cached_property
        def expensive_computation(self):
            return compute()

        @classproperty
        def count(cls):
            return cls._instances
"""

from typing import Any, Callable, Optional, Type
import functools
import threading


class cached_property:
    """
    Decorator for caching property values.

    The property value is computed once and cached on the instance.

    Example:
        class DataProcessor:
            @cached_property
            def processed_data(self):
                # Expensive computation
                return [x * 2 for x in range(1000000)]

        processor = DataProcessor()
        data = processor.processed_data  # Computed here
        data = processor.processed_data  # Cached, returns immediately
    """

    def __init__(self, func: Callable):
        self.func = func
        self.__doc__ = func.__doc__
        self.__name__ = func.__name__
        self.__module__ = func.__module__

    def __get__(self, instance: Any, owner: Type = None) -> Any:
        if instance is None:
            return self

        # Compute and cache value
        value = self.func(instance)

        # Store in instance __dict__
        instance.__dict__[self.__name__] = value

        return value

    def __set__(self, instance: Any, value: Any) -> None:
        instance.__dict__[self.__name__] = value

    def __delete__(self, instance: Any) -> None:
        instance.__dict__.pop(self.__name__, None)


class classproperty:
    """
    Decorator for class-level properties.

    Example:
        class Model:
            _objects = []

            @classproperty
            def objects(cls):
                return cls._objects

        Model.objects  # Returns _objects list
    """

    def __init__(self, func: Callable):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, instance: Any, owner: Type = None) -> Any:
        return self.func(owner)

    def __set__(self, instance: Any, value: Any) -> None:
        raise AttributeError("classproperty is read-only")


class cached_method:
    """
    Decorator for caching method results.

    Unlike cached_property, this works with methods that take arguments.

    Example:
        class Calculator:
            @cached_method
            def fibonacci(self, n):
                if n <= 1:
                    return n
                return self.fibonacci(n-1) + self.fibonacci(n-2)

        calc = Calculator()
        calc.fibonacci(50)  # Cached intermediate results
    """

    def __init__(self, func: Callable):
        self.func = func
        self.cache = {}
        self._lock = threading.Lock()
        functools.update_wrapper(self, func)

    def __get__(self, instance: Any, owner: Type = None) -> Any:
        if instance is None:
            return self

        # Create bound method with cache
        return functools.partial(self._call, instance)

    def _call(self, instance: Any, *args, **kwargs) -> Any:
        # Create cache key
        key = (args, tuple(sorted(kwargs.items())))

        # Check cache
        with self._lock:
            if key not in self.cache:
                self.cache[key] = self.func(instance, *args, **kwargs)

        return self.cache[key]

    def clear_cache(self) -> None:
        """Clear the method cache."""
        with self._lock:
            self.cache.clear()


class classonlymethod:
    """
    Decorator for methods that can only be called on the class.

    Example:
        class Model:
            @classonlymethod
            def create(cls, **kwargs):
                return cls(**kwargs)

        Model.create(name='test')  # OK
        model = Model()
        model.create()  # Error!
    """

    def __init__(self, func: Callable):
        self.func = func
        functools.update_wrapper(self, func)

    def __get__(self, instance: Any, owner: Type = None) -> Any:
        if instance is not None:
            raise TypeError(
                f"{self.func.__name__}() is a classonly method and cannot be called on instances"
            )
        return self.func.__get__(owner, owner)


def memoize(func: Callable = None, *, maxsize: int = 128):
    """
    Decorator for memoizing function results.

    Args:
        func: Function to memoize
        maxsize: Maximum cache size

    Returns:
        Memoized function

    Example:
        @memoize
        def expensive_function(n):
            return sum(range(n))
    """
    def decorator(f):
        cache = {}
        lock = threading.Lock()

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))

            with lock:
                if key in cache:
                    return cache[key]

                result = f(*args, **kwargs)

                # Enforce maxsize
                if maxsize and len(cache) >= maxsize:
                    cache.pop(next(iter(cache)))

                cache[key] = result

            return result

        wrapper.cache = cache
        wrapper.clear_cache = lambda: cache.clear()

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def throttle(seconds: float = 1.0):
    """
    Decorator to throttle function calls.

    Args:
        seconds: Minimum time between calls

    Example:
        @throttle(seconds=5)
        def send_notification():
            # Will only be called once every 5 seconds
            pass
    """
    def decorator(func):
        last_called = [0.0]
        lock = threading.Lock()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time

            with lock:
                now = time.time()
                if now - last_called[0] >= seconds:
                    last_called[0] = now
                    return func(*args, **kwargs)
                return None

        return wrapper
    return decorator


def debounce(seconds: float = 0.1):
    """
    Decorator to debounce function calls.

    The function is only called after a period of no calls.

    Args:
        seconds: Wait time before calling

    Example:
        @debounce(seconds=0.5)
        def save_draft():
            # Only saves after user stops typing
            pass
    """
    def decorator(func):
        timer = [None]
        lock = threading.Lock()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import threading
            import time

            def call_func():
                func(*args, **kwargs)

            with lock:
                if timer[0] is not None:
                    timer[0].cancel()

                timer[0] = threading.Timer(seconds, call_func)
                timer[0].start()

        return wrapper
    return decorator


class Singleton(type):
    """
    Metaclass for singleton classes.

    Example:
        class Database(metaclass=Singleton):
            def __init__(self):
                self.connected = False

        db1 = Database()
        db2 = Database()
        db1 is db2  # True
    """

    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
