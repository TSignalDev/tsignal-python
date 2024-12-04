"""
Implementation of the Signal class for tsignal.

Provides signal-slot communication pattern for event handling, supporting both
synchronous and asynchronous operations in a thread-safe manner.
"""

import asyncio
import functools
import logging
import threading
from enum import Enum
from typing import Callable, List, Tuple, Optional, Union


class TConnectionType(Enum):
    """Connection type for signal-slot connections."""
    DIRECT_CONNECTION = 1
    QUEUED_CONNECTION = 2


class _SignalConstants:
    """Constants for signal-slot communication."""
    FROM_EMIT = "_from_emit"
    THREAD = "_thread"
    LOOP = "_loop"


# Initialize logger
logger = logging.getLogger(__name__)


def _wrap_direct_function(func):
    """Wrapper for directly connected functions"""
    is_coroutine = asyncio.iscoroutinefunction(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Wrapper for directly connected functions"""
        # Remove FROM_EMIT
        kwargs.pop(_SignalConstants.FROM_EMIT, False)

        # DIRECT_CONNECTION executes immediately regardless of thread
        if is_coroutine:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.create_task(func(*args, **kwargs))
        return func(*args, **kwargs)

    return wrapper


class TSignal:
    """Signal class for tsignal."""
    def __init__(self):
        self.connections: List[Tuple[Optional[object], Callable, TConnectionType]] = []

    def connect(
        self, receiver_or_slot: Union[object, Callable], slot: Optional[Callable] = None
    ):
        """Connect signal to a slot."""
        if slot is None:
            if not callable(receiver_or_slot):
                logger.error(
                    "Invalid connection attempt - receiver_or_slot is not callable: %s",
                    receiver_or_slot,
                )
                raise TypeError("When slot is not provided, receiver must be callable")

            receiver = None

            if hasattr(receiver_or_slot, "__self__"):
                obj = receiver_or_slot.__self__
                if hasattr(obj, _SignalConstants.THREAD) and hasattr(
                    obj, _SignalConstants.LOOP
                ):
                    receiver = obj
                    slot = receiver_or_slot
                else:
                    slot = _wrap_direct_function(receiver_or_slot)
            else:
                slot = _wrap_direct_function(receiver_or_slot)
        else:
            if receiver_or_slot is None:
                logger.error("Invalid connection attempt - receiver cannot be None")
                raise AttributeError("Receiver cannot be None")
            receiver = receiver_or_slot
            if not callable(slot):
                logger.error(
                    "Invalid connection attempt - slot is not callable: %s",
                    slot,
                )
                raise TypeError("Slot must be callable")

        is_coroutine = asyncio.iscoroutinefunction(slot)
        conn_type = (
            TConnectionType.QUEUED_CONNECTION
            if is_coroutine
            else TConnectionType.DIRECT_CONNECTION
        )
        self.connections.append((receiver, slot, conn_type))

    def disconnect(self, receiver: object = None, slot: Callable = None) -> int:
        """Disconnect signal from slot(s)."""
        if receiver is None and slot is None:
            logger.debug("Disconnecting all slots")
            count = len(self.connections)
            self.connections.clear()
            return count

        original_count = len(self.connections)
        new_connections = []

        for r, s, t in self.connections:
            # Compare original function and wrapped function for directly connected functions
            if r is None and slot is not None:
                if getattr(s, "__wrapped__", None) == slot or s == slot:
                    continue
            elif (receiver is None or r == receiver) and (slot is None or s == slot):
                continue
            new_connections.append((r, s, t))

        self.connections = new_connections
        disconnected = original_count - len(self.connections)
        logger.debug("Disconnected %d connection(s)", disconnected)
        return disconnected

    def emit(self, *args, **kwargs):
        """Emit signal to connected slots."""
        logger.debug("Signal emission started")

        for receiver, slot, conn_type in self.connections:
            try:
                if conn_type == TConnectionType.DIRECT_CONNECTION:
                    slot(*args, **kwargs)
                else:  # QUEUED_CONNECTION
                    receiver_loop = getattr(receiver, "_loop", None)
                    if not receiver_loop:
                        logger.error("No event loop found for receiver")
                        continue

                    is_coroutine = asyncio.iscoroutinefunction(slot)
                    if is_coroutine:

                        def create_task_wrapper(s=slot):
                            task = asyncio.create_task(s(*args, **kwargs))
                            return task

                        receiver_loop.call_soon_threadsafe(create_task_wrapper)
                    else:

                        def call_wrapper(s=slot):
                            s(*args, **kwargs)

                        receiver_loop.call_soon_threadsafe(call_wrapper)

            except Exception as e:
                logger.error("Error in signal emission: %s", e, exc_info=True)


def t_signal(func):
    """Signal decorator"""
    sig_name = func.__name__

    @property
    def wrapper(self):
        if not hasattr(self, f"_{sig_name}"):
            setattr(self, f"_{sig_name}", TSignal())
        return getattr(self, f"_{sig_name}")

    return wrapper


def t_slot(func):
    """Slot decorator"""
    is_coroutine = asyncio.iscoroutinefunction(func)

    if is_coroutine:

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            """Wrapper for coroutine slots"""
            from_emit = kwargs.pop(_SignalConstants.FROM_EMIT, False)

            if not hasattr(self, _SignalConstants.THREAD):
                self._thread = threading.current_thread()

            if not hasattr(self, _SignalConstants.LOOP):
                try:
                    self._loop = asyncio.get_running_loop()
                except RuntimeError:
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)

            if not from_emit:
                current_thread = threading.current_thread()
                if current_thread != self._thread:
                    logger.debug("Executing coroutine slot from different thread")
                    future = asyncio.run_coroutine_threadsafe(
                        func(self, *args, **kwargs), self._loop
                    )
                    return await asyncio.wrap_future(future)

            return await func(self, *args, **kwargs)

    else:

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            """Wrapper for regular slots"""
            from_emit = kwargs.pop(_SignalConstants.FROM_EMIT, False)

            if not hasattr(self, _SignalConstants.THREAD):
                self._thread = threading.current_thread()

            if not hasattr(self, _SignalConstants.LOOP):
                try:
                    self._loop = asyncio.get_running_loop()
                except RuntimeError:
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)

            if not from_emit:
                current_thread = threading.current_thread()
                if current_thread != self._thread:
                    logger.debug("Executing regular slot from different thread")
                    self._loop.call_soon_threadsafe(lambda: func(self, *args, **kwargs))
                    return None

            return func(self, *args, **kwargs)

    return wrapper


def t_with_signals(cls):
    """Decorator for classes using signals"""
    original_init = cls.__init__

    def __init__(self, *args, **kwargs):
        # Set thread and event loop
        self._thread = threading.current_thread()
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        # Call the original __init__
        original_init(self, *args, **kwargs)

    cls.__init__ = __init__
    return cls
