"""
FastStack Signals Module

Provides a signal/hook system for pre/post operations on models.
Similar to Django signals but with async support.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from weakref import WeakSet


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


class SignalManager:
    """
    Central manager for signals and receivers.
    """

    def __init__(self):
        """Initialize signal manager."""
        self._receivers: dict[SignalType, list[Receiver]] = {
            st: [] for st in SignalType
        }
        self._weak_refs: WeakSet = WeakSet()

    def connect(
        self,
        signal_type: SignalType,
        callback: Callable,
        sender: type | None = None,
        dispatch_uid: str | None = None,
        weak: bool = True,
    ) -> None:
        """
        Connect a receiver to a signal.

        Args:
            signal_type: Type of signal to listen for
            callback: Function to call when signal is emitted
            sender: Only listen for signals from this sender
            dispatch_uid: Unique identifier for this receiver
            weak: Use weak reference to callback
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
        )

        self._receivers[signal_type].append(receiver)

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
        **kwargs,
    ) -> list[Any]:
        """
        Emit a signal to all connected receivers.

        Args:
            signal_type: Type of signal
            sender: Sender class
            instance: Instance the signal is about
            **kwargs: Additional signal data

        Returns:
            List of return values from receivers
        """
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
            except Exception as e:
                # Log error but continue to other receivers
                print(f"[SIGNAL ERROR] {signal_type.value}: {e}")

        return results

    async def send_async(
        self,
        signal_type: SignalType,
        sender: type | None = None,
        instance: Any | None = None,
        **kwargs,
    ) -> list[Any]:
        """
        Emit a signal asynchronously.

        Args:
            signal_type: Type of signal
            sender: Sender class
            instance: Instance the signal is about
            **kwargs: Additional signal data

        Returns:
            List of return values from receivers
        """
        import asyncio

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


# Global signal manager
signal_manager = SignalManager()


# Decorator for connecting to signals
def receiver(signal_type: SignalType, sender: type | None = None, dispatch_uid: str | None = None):
    """
    Decorator to connect a function to a signal.

    Usage:
        @receiver(SignalType.POST_SAVE, sender=User)
        def user_created(signal):
            print(f"User created: {signal.instance}")
    """
    def decorator(func: Callable) -> Callable:
        signal_manager.connect(signal_type, func, sender, dispatch_uid)
        return func
    return decorator


# Convenience functions
def pre_save(callback: Callable, sender: type | None = None):
    """Connect to pre_save signal."""
    signal_manager.connect(SignalType.PRE_SAVE, callback, sender)


def post_save(callback: Callable, sender: type | None = None):
    """Connect to post_save signal."""
    signal_manager.connect(SignalType.POST_SAVE, callback, sender)


def pre_delete(callback: Callable, sender: type | None = None):
    """Connect to pre_delete signal."""
    signal_manager.connect(SignalType.PRE_DELETE, callback, sender)


def post_delete(callback: Callable, sender: type | None = None):
    """Connect to post_delete signal."""
    signal_manager.connect(SignalType.POST_DELETE, callback, sender)


def pre_update(callback: Callable, sender: type | None = None):
    """Connect to pre_update signal."""
    signal_manager.connect(SignalType.PRE_UPDATE, callback, sender)


def post_update(callback: Callable, sender: type | None = None):
    """Connect to post_update signal."""
    signal_manager.connect(SignalType.POST_UPDATE, callback, sender)


def pre_create(callback: Callable, sender: type | None = None):
    """Connect to pre_create signal."""
    signal_manager.connect(SignalType.PRE_CREATE, callback, sender)


def post_create(callback: Callable, sender: type | None = None):
    """Connect to post_create signal."""
    signal_manager.connect(SignalType.POST_CREATE, callback, sender)
