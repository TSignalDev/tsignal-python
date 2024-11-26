# Standard library imports
import asyncio
import functools
import logging
import threading
from enum import Enum
from typing import Callable, List, Tuple


class TConnectionType(Enum):
    DirectConnection = 1
    QueuedConnection = 2


class TSignalConstants:
    FROM_EMIT = "_from_emit"
    THREAD = "_thread"
    LOOP = "_loop"


# Initialize logger
logger = logging.getLogger(__name__)


class TSignal:
    def __init__(self, owner):
        """Initialize signal"""
        self.owner = owner
        self.connections: List[Tuple[object, str, TConnectionType]] = []
        logger.debug(f"Signal initialized for {owner.__class__.__name__}")

    def connect(self, receiver: object, slot: Callable):
        """Connect signal to a slot"""
        if receiver is None:
            raise AttributeError("Cannot connect to None receiver")
        if not callable(slot):
            raise TypeError("Slot must be callable")

        logger.debug(
            f"Connecting {receiver.__class__.__name__}.{slot.__name__} "
            f"to {self.owner.__class__.__name__}"
        )

        is_coroutine = asyncio.iscoroutinefunction(slot)
        conn_type = (
            TConnectionType.QueuedConnection
            if is_coroutine
            or threading.current_thread()
            != getattr(receiver, TSignalConstants.THREAD, None)
            else TConnectionType.DirectConnection
        )

        self.connections.append((receiver, slot, conn_type))
        logger.debug(f"Connection established with type: {conn_type.name}")

    def disconnect(self, receiver: object = None, slot: Callable = None) -> int:
        """
        Disconnect signal from slot(s).

        Args:
            receiver: Specific receiver object to disconnect. If None, matches any receiver.
            slot: Specific slot to disconnect. If None, matches any slot.

        Returns:
            Number of disconnected connections
        """
        if receiver is None and slot is None:
            logger.debug(
                f"Disconnecting all slots from {self.owner.__class__.__name__}"
            )
            count = len(self.connections)
            self.connections.clear()
            return count

        original_count = len(self.connections)
        new_connections = []

        for r, s, t in self.connections:
            if (receiver is None or r == receiver) and (slot is None or s == slot):
                logger.debug(
                    f"Disconnecting {r.__class__.__name__}.{s.__name__} "
                    f"from {self.owner.__class__.__name__}"
                )
                continue
            new_connections.append((r, s, t))

        self.connections = new_connections
        disconnected = original_count - len(self.connections)

        if disconnected > 0:
            logger.debug(
                f"Disconnected {disconnected} connection(s) from {self.owner.__class__.__name__}"
            )
        else:
            logger.debug(
                f"No matching connections found to disconnect in {self.owner.__class__.__name__}"
            )

        return disconnected

    def emit(self, *args, **kwargs):
        logger.debug(
            f"Signal emission from {self.owner.__class__.__name__} "
            f"with {len(self.connections)} connections"
        )

        current_loop = asyncio.get_event_loop()
        logger.debug(
            f"Current event loop: {current_loop}, running: {current_loop.is_running()}"
        )

        kwargs[TSignalConstants.FROM_EMIT] = True

        for receiver, slot, conn_type in self.connections:
            logger.debug(f"Processing {receiver.__class__.__name__}.{slot.__name__}")

            receiver_loop = getattr(receiver, TSignalConstants.LOOP, None)
            if not receiver_loop:
                logger.error(
                    f"No event loop found for receiver {receiver.__class__.__name__}"
                )
                continue

            is_coroutine = asyncio.iscoroutinefunction(slot)
            logger.debug(f"Is coroutine: {is_coroutine}")

            try:
                if conn_type == TConnectionType.DirectConnection:
                    logger.debug("Executing regular function directly")
                    slot(*args, **kwargs)
                else:  # QueuedConnection
                    if is_coroutine:
                        logger.debug("Creating async task")

                        def create_task_wrapper(s=slot):
                            task = asyncio.create_task(s(*args, **kwargs))
                            logger.debug(f"Created task: {task}")
                            return task

                        receiver_loop.call_soon_threadsafe(create_task_wrapper)
                        logger.debug("Task creation scheduled")
                    else:
                        logger.debug("Scheduling regular function via QueuedConnection")

                        def call_wrapper(s=slot):
                            s(*args, **kwargs)

                        receiver_loop.call_soon_threadsafe(call_wrapper)
                        logger.debug("Regular function scheduled")
            except Exception as e:
                logger.error(
                    f"Error in signal emission to {receiver.__class__.__name__}.{slot.__name__}: {e}",
                    exc_info=True,
                )


def t_signal(func):
    """Signal decorator"""
    sig_name = func.__name__

    @property
    def wrapper(self):
        if not hasattr(self, f"_{sig_name}"):
            setattr(self, f"_{sig_name}", TSignal(self))
        return getattr(self, f"_{sig_name}")

    return wrapper


def t_slot(func):
    """Slot decorator"""
    is_coroutine = asyncio.iscoroutinefunction(func)

    if is_coroutine:

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            from_emit = kwargs.pop(TSignalConstants.FROM_EMIT, False)

            if not hasattr(self, TSignalConstants.THREAD):
                self._thread = threading.current_thread()
                logger.debug(
                    f"Set thread for {self.__class__.__name__}: {self._thread}"
                )

            if not hasattr(self, TSignalConstants.LOOP):
                try:
                    self._loop = asyncio.get_running_loop()
                except RuntimeError:
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)
                    logger.debug(
                        f"Created new event loop for {self.__class__.__name__}"
                    )

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
            from_emit = kwargs.pop(TSignalConstants.FROM_EMIT, False)

            if not hasattr(self, TSignalConstants.THREAD):
                self._thread = threading.current_thread()
                logger.debug(
                    f"Set thread for {self.__class__.__name__}: {self._thread}"
                )

            if not hasattr(self, TSignalConstants.LOOP):
                try:
                    self._loop = asyncio.get_running_loop()
                except RuntimeError:
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)
                    logger.debug(
                        f"Created new event loop for {self.__class__.__name__}"
                    )

            if not from_emit:
                current_thread = threading.current_thread()
                if current_thread != self._thread:
                    logger.debug("Executing regular slot from different thread")
                    self._loop.call_soon_threadsafe(lambda: func(self, *args, **kwargs))
                    return

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
