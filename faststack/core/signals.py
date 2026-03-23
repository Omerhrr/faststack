"""
FastStack Signals Module

Provides a signal/hook system for pre/post operations on models.
Similar to Django signals but with async support.

Features:
- Recursion detection to prevent infinite loops
- Priority-based ordering
- Async support
- Error handling options
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from weakref import WeakSet
import threading
import asyncio


class SignalType(Enum):
    """Types of signals."""
    PRE_SAVE = "pre_save"
    POST_SAVE = "post_save"
    PRE_DELETE = "pre_delete"
    POST_DELETE = "post_delete"
    PRE_UPDATE = "pre_update"
    POST_UPDATE = "post_update"
    PRE_CREATE = "pre_create"
    POST_CREATE = "post_create"


@dataclass
class Signal:
    """
    Represents a signal that can be emitted and received.
    """
    name: str
    type: SignalType
    sender: type | None = None
    instance: Any | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Receiver:
    """
    Represents a signal receiver.
    """
    signal_type: SignalType
    sender: type | None
    callback: Callable
    dispatch_uid: str | None = None
    weak: bool = True
    priority: int = 100  # Lower number = higher priority


class RecursionDetectedError(Exception):
    """Raised when signal recursion is detected."""
    pass


class SignalManager:
    """
    Central manager for signals and receivers.
    
    Features:
    - Recursion detection to prevent infinite loops
    - Priority-based callback ordering
    - Configurable error handling
    """

    def __init__(self, max_recursion_depth: int = 3):
        """Initialize signal manager.
        
        Args:
            max_recursion_depth: Maximum allowed recursion depth for same signal/sender
        """
        self._receivers: dict[SignalType, list[Receiver]] = {
            st: [] for st in SignalType
        }
        self._weak_refs: WeakSet = WeakSet()
        self.max_recursion_depth = max_recursion_depth
        
        # Thread-local storage for recursion tracking
        self._recursion_stack = threading.local()
        self._async_recursion_stack: dict[int, dict] = {}
    
    def _get_recursion_key(self, signal_type: SignalType, sender: type | None, instance: Any | None) -> str:
        """Generate a unique key for recursion tracking."""
        sender_name = sender.__name__ if sender else "None"
        instance_id = id(instance) if instance else "None"
        return f"{signal_type.value}:{sender_name}:{instance_id}"
    
    def _check_recursion(self, signal_type: SignalType, sender: type | None, instance: Any | None) -> int:
        """
        Check and track recursion depth.
        
        Returns:
            Current recursion depth
            
        Raises:
            RecursionDetectedError: If max recursion depth exceeded
        """
        if not hasattr(self._recursion_stack, 'depths'):
            self._recursion_stack.depths = {}
        
        key = self._get_recursion_key(signal_type, sender, instance)
        current_depth = self._recursion_stack.depths.get(key, 0)
        
        if current_depth >= self.max_recursion_depth:
            raise RecursionDetectedError(
                f"Signal recursion detected: {key} called {current_depth + 1} times. "
                f"Maximum allowed depth is {self.max_recursion_depth}. "
                f"This usually indicates a signal handler that triggers itself."
            )
        
        self._recursion_stack.depths[key] = current_depth + 1
        return current_depth + 1
    
    def _release_recursion(self, signal_type: SignalType, sender: type | None, instance: Any | None) -> None:
        """Release recursion tracking after signal completes."""
        if not hasattr(self._recursion_stack, 'depths'):
            return
        
        key = self._get_recursion_key(signal_type, sender, instance)
        current_depth = self._recursion_stack.depths.get(key, 1)
        
        if current_depth <= 1:
            del self._recursion_stack.depths[key]
        else:
            self._recursion_stack.depths[key] = current_depth - 1
    
    async def _check_async_recursion(self, signal_type: SignalType, sender: type | None, instance: Any | None) -> int:
        """Check recursion depth for async signals."""
        task_id = id(asyncio.current_task()) if asyncio.current_task() else 0
        
        if task_id not in self._async_recursion_stack:
            self._async_recursion_stack[task_id] = {}
        
        key = self._get_recursion_key(signal_type, sender, instance)
        current_depth = self._async_recursion_stack[task_id].get(key, 0)
        
        if current_depth >= self.max_recursion_depth:
            raise RecursionDetectedError(
                f"Signal recursion detected: {key} called {current_depth + 1} times. "
                f"Maximum allowed depth is {self.max_recursion_depth}."
            )
        
        self._async_recursion_stack[task_id][key] = current_depth + 1
        return current_depth + 1
    
    async def _release_async_recursion(self, signal_type: SignalType, sender: type | None, instance: Any | None) -> None:
        """Release async recursion tracking."""
        task_id = id(asyncio.current_task()) if asyncio.current_task() else 0
        
        if task_id not in self._async_recursion_stack:
            return
        
        key = self._get_recursion_key(signal_type, sender, instance)
        current_depth = self._async_recursion_stack[task_id].get(key, 1)
        
        if current_depth <= 1:
            del self._async_recursion_stack[task_id][key]
            if not self._async_recursion_stack[task_id]:
                del self._async_recursion_stack[task_id]
        else:
            self._async_recursion_stack[task_id][key] = current_depth - 1

    def connect(
        self,
        signal_type: SignalType,
        callback: Callable,
        sender: type | None = None,
        dispatch_uid: str | None = None,
        weak: bool = True,
        priority: int = 100,
    ) -> None:
        """
        Connect a receiver to a signal.

        Args:
            signal_type: Type of signal to listen for
            callback: Function to call when signal is emitted
            sender: Only listen for signals from this sender
            dispatch_uid: Unique identifier for this receiver
            weak: Use weak reference to callback
            priority: Priority (lower = higher priority, called first)
        """
        # Check if receiver with this uid already exists
        if dispatch_uid:
            for receiver in self._receivers[signal_type]:
                if receiver.dispatch_uid == dispatch_uid:
                    return  # Already connected

        receiver = Receiver(
            signal_type=signal_type,
            sender=sender,
            callback=callback,
            dispatch_uid=dispatch_uid,
            weak=weak,
            priority=priority,
        )

        self._receivers[signal_type].append(receiver)
        
        # Sort by priority (lower number = higher priority)
        self._receivers[signal_type].sort(key=lambda r: r.priority)

    def disconnect(
        self,
        signal_type: SignalType,
        callback: Callable | None = None,
        dispatch_uid: str | None = None,
    ) -> bool:
        """
        Disconnect a receiver from a signal.

        Args:
            signal_type: Type of signal
            callback: Callback to disconnect
            dispatch_uid: UID of receiver to disconnect

        Returns:
            True if receiver was disconnected
        """
        receivers = self._receivers[signal_type]

        for i, receiver in enumerate(receivers):
            if callback and receiver.callback == callback:
                receivers.pop(i)
                return True
            if dispatch_uid and receiver.dispatch_uid == dispatch_uid:
                receivers.pop(i)
                return True

        return False

    def send(
        self,
        signal_type: SignalType,
        sender: type | None = None,
        instance: Any | None = None,
        raise_on_recursion: bool = True,
        **kwargs,
    ) -> list[Any]:
        """
        Emit a signal to all connected receivers.
        
        Includes recursion detection to prevent infinite loops.

        Args:
            signal_type: Type of signal
            sender: Sender class
            instance: Instance the signal is about
            raise_on_recursion: Whether to raise error on recursion (default: True)
            **kwargs: Additional signal data

        Returns:
            List of return values from receivers
            
        Raises:
            RecursionDetectedError: If recursion detected and raise_on_recursion=True
        """
        # Check recursion
        try:
            depth = self._check_recursion(signal_type, sender, instance)
        except RecursionDetectedError:
            if raise_on_recursion:
                raise
            return []

        try:
            signal = Signal(
                name=signal_type.value,
                type=signal_type,
                sender=sender,
                instance=instance,
                data=kwargs,
            )

            results = []

            for receiver in self._receivers[signal_type]:
                # Check if receiver wants this sender
                if receiver.sender is not None and receiver.sender != sender:
                    continue

                try:
                    result = receiver.callback(signal)
                    results.append(result)
                except RecursionDetectedError:
                    # Re-raise recursion errors
                    raise
                except Exception as e:
                    # Log error but continue to other receivers
                    print(f"[SIGNAL ERROR] {signal_type.value} in {receiver.callback.__name__}: {e}")

            return results
        finally:
            self._release_recursion(signal_type, sender, instance)

    async def send_async(
        self,
        signal_type: SignalType,
        sender: type | None = None,
        instance: Any | None = None,
        raise_on_recursion: bool = True,
        **kwargs,
    ) -> list[Any]:
        """
        Emit a signal asynchronously.

        Args:
            signal_type: Type of signal
            sender: Sender class
            instance: Instance the signal is about
            raise_on_recursion: Whether to raise error on recursion
            **kwargs: Additional signal data

        Returns:
            List of return values from receivers
        """
        # Check async recursion
        try:
            depth = await self._check_async_recursion(signal_type, sender, instance)
        except RecursionDetectedError:
            if raise_on_recursion:
                raise
            return []

        try:
            signal = Signal(
                name=signal_type.value,
                type=signal_type,
                sender=sender,
                instance=instance,
                data=kwargs,
            )

            results = []
            tasks = []

            for receiver in self._receivers[signal_type]:
                if receiver.sender is not None and receiver.sender != sender:
                    continue

                try:
                    # Check if callback is async
                    if asyncio.iscoroutinefunction(receiver.callback):
                        tasks.append(receiver.callback(signal))
                    else:
                        # Run sync callback in executor
                        loop = asyncio.get_event_loop()
                        tasks.append(loop.run_in_executor(None, receiver.callback, signal))
                except Exception as e:
                    print(f"[SIGNAL ERROR] {signal_type.value}: {e}")

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)

            return results
        finally:
            await self._release_async_recursion(signal_type, sender, instance)


# Global signal manager
signal_manager = SignalManager()


# Decorator for connecting to signals
def receiver(
    signal_type: SignalType,
    sender: type | None = None,
    dispatch_uid: str | None = None,
    priority: int = 100,
):
    """
    Decorator to connect a function to a signal.

    Usage:
        @receiver(SignalType.POST_SAVE, sender=User)
        def user_created(signal):
            print(f"User created: {signal.instance}")
    """
    def decorator(func: Callable) -> Callable:
        signal_manager.connect(signal_type, func, sender, dispatch_uid, priority=priority)
        return func
    return decorator


# Convenience functions
def pre_save(callback: Callable, sender: type | None = None, priority: int = 100):
    """Connect to pre_save signal."""
    signal_manager.connect(SignalType.PRE_SAVE, callback, sender, priority=priority)


def post_save(callback: Callable, sender: type | None = None, priority: int = 100):
    """Connect to post_save signal."""
    signal_manager.connect(SignalType.POST_SAVE, callback, sender, priority=priority)


def pre_delete(callback: Callable, sender: type | None = None, priority: int = 100):
    """Connect to pre_delete signal."""
    signal_manager.connect(SignalType.PRE_DELETE, callback, sender, priority=priority)


def post_delete(callback: Callable, sender: type | None = None, priority: int = 100):
    """Connect to post_delete signal."""
    signal_manager.connect(SignalType.POST_DELETE, callback, sender, priority=priority)


def pre_update(callback: Callable, sender: type | None = None, priority: int = 100):
    """Connect to pre_update signal."""
    signal_manager.connect(SignalType.PRE_UPDATE, callback, sender, priority=priority)


def post_update(callback: Callable, sender: type | None = None, priority: int = 100):
    """Connect to post_update signal."""
    signal_manager.connect(SignalType.POST_UPDATE, callback, sender, priority=priority)


def pre_create(callback: Callable, sender: type | None = None, priority: int = 100):
    """Connect to pre_create signal."""
    signal_manager.connect(SignalType.PRE_CREATE, callback, sender, priority=priority)


def post_create(callback: Callable, sender: type | None = None, priority: int = 100):
    """Connect to post_create signal."""
    signal_manager.connect(SignalType.POST_CREATE, callback, sender, priority=priority)
