# src/tsignal/core.py

"""
Implementation of the Signal class for tsignal.

Provides signal-slot communication pattern for event handling, supporting both
synchronous and asynchronous operations in a thread-safe manner.
"""

from enum import Enum
import asyncio
import concurrent.futures
import contextvars
import functools
import logging
import threading
from typing import Callable
from tsignal.utils import t_signal_log_and_raise_error

logger = logging.getLogger(__name__)


class TSignalConstants:
    """Constants for signal-slot communication."""

    FROM_EMIT = "_tsignal_from_emit"
    THREAD = "_tsignal_thread"
    LOOP = "_tsignal_loop"
    AFFINITY = "_tsignal_affinity"


_tsignal_from_emit = contextvars.ContextVar(TSignalConstants.FROM_EMIT, default=False)


class TConnectionType(Enum):
    """Connection type for signal-slot connections."""

    DIRECT_CONNECTION = 1
    QUEUED_CONNECTION = 2
    AUTO_CONNECTION = 3


def _wrap_standalone_function(func, is_coroutine):
    """Wrap standalone function"""

    @functools.wraps(func)
    def wrap(*args, **kwargs):
        """Wrap standalone function"""

        # pylint: disable=no-else-return
        if is_coroutine:
            # Call coroutine function -> return coroutine object
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                t_signal_log_and_raise_error(
                    logger,
                    RuntimeError,
                    (
                        "[TSignal][_wrap_standalone_function] No running event loop found. "
                        "A running loop is required for coroutine slots."
                    ),
                )

            return func(*args, **kwargs)
        else:
            # Call sync function -> return result
            return func(*args, **kwargs)

    return wrap


def _determine_connection_type(conn_type, receiver, owner, is_coro_slot):
    """
    Determine the actual connection type based on the given parameters.
    This logic was originally inside emit, but is now extracted for easier testing.
    """
    actual_conn_type = conn_type

    if conn_type == TConnectionType.AUTO_CONNECTION:
        if is_coro_slot:
            actual_conn_type = TConnectionType.QUEUED_CONNECTION
        else:
            if (
                receiver is not None
                and hasattr(receiver, TSignalConstants.THREAD)
                and hasattr(owner, TSignalConstants.THREAD)
                and hasattr(receiver, TSignalConstants.AFFINITY)
                and hasattr(owner, TSignalConstants.AFFINITY)
            ):
                if receiver._tsignal_affinity == owner._tsignal_affinity:
                    actual_conn_type = TConnectionType.DIRECT_CONNECTION
                else:
                    actual_conn_type = TConnectionType.QUEUED_CONNECTION
            else:
                actual_conn_type = TConnectionType.DIRECT_CONNECTION

    return actual_conn_type


class TSignal:
    """Signal class for tsignal."""

    def __init__(self):
        self.connections = []
        self.owner = None

    def connect(
        self, receiver_or_slot, slot=None, conn_type=TConnectionType.AUTO_CONNECTION
    ):
        """
        Connect signal to a slot with an optional connection type.
        If conn_type is AUTO_CONNECTION, the actual type (direct or queued)
        is determined at emit time based on threads.
        """

        logger.debug(
            "[TSignal][connect][START] class=%s receiver_or_slot=%s slot=%s",
            self.__class__.__name__,
            receiver_or_slot,
            slot,
        )

        if slot is None:
            if not callable(receiver_or_slot):
                t_signal_log_and_raise_error(
                    logger,
                    TypeError,
                    "[TSignal][connect] receiver_or_slot must be callable.",
                )

            receiver = None

            is_coro_slot = asyncio.iscoroutinefunction(
                receiver_or_slot.__func__
                if hasattr(receiver_or_slot, "__self__")
                else receiver_or_slot
            )

            if hasattr(receiver_or_slot, "__self__"):
                obj = receiver_or_slot.__self__
                if hasattr(obj, TSignalConstants.THREAD) and hasattr(
                    obj, TSignalConstants.LOOP
                ):
                    receiver = obj
                    slot = receiver_or_slot
                else:
                    slot = _wrap_standalone_function(receiver_or_slot, is_coro_slot)
            else:
                slot = _wrap_standalone_function(receiver_or_slot, is_coro_slot)
        else:
            # when both receiver and slot are provided
            if receiver_or_slot is None:
                t_signal_log_and_raise_error(
                    logger,
                    AttributeError,
                    "[TSignal][connect] Receiver cannot be None.",
                )
            if not callable(slot):
                t_signal_log_and_raise_error(
                    logger, TypeError, "[TSignal][connect] Slot must be callable."
                )

            receiver = receiver_or_slot
            is_coro_slot = asyncio.iscoroutinefunction(slot)

        # when conn_type is AUTO, it is not determined here.
        # it is determined at emit time, so it is just stored.
        # If DIRECT or QUEUED is specified, it is used as it is.
        # However, when AUTO is specified, it is determined by thread comparison at emit time.
        if conn_type not in (
            TConnectionType.AUTO_CONNECTION,
            TConnectionType.DIRECT_CONNECTION,
            TConnectionType.QUEUED_CONNECTION,
        ):
            t_signal_log_and_raise_error(logger, ValueError, "Invalid connection type.")

        conn = (receiver, slot, conn_type, is_coro_slot)
        logger.debug("[TSignal][connect][END] conn=%s", conn)

        self.connections.append(conn)

    def disconnect(self, receiver: object = None, slot: Callable = None) -> int:
        """Disconnect signal from slot(s)."""

        if receiver is None and slot is None:
            count = len(self.connections)
            self.connections.clear()
            return count

        original_count = len(self.connections)
        new_connections = []

        for r, s, t, c in self.connections:
            # Compare original function and wrapped function for directly connected functions
            if r is None and slot is not None:
                if getattr(s, "__wrapped__", None) == slot or s == slot:
                    continue
            elif (receiver is None or r == receiver) and (slot is None or s == slot):
                continue
            new_connections.append((r, s, t, c))

        self.connections = new_connections
        disconnected = original_count - len(self.connections)

        return disconnected

    def emit(self, *args, **kwargs):
        """Emit signal to connected slots."""

        logger.debug("[TSignal][emit][START]")

        token = _tsignal_from_emit.set(True)

        # pylint: disable=too-many-nested-blocks
        try:
            for receiver, slot, conn_type, is_coro_slot in self.connections:
                actual_conn_type = _determine_connection_type(
                    conn_type, receiver, self.owner, is_coro_slot
                )

                logger.debug(
                    "[TSignal][emit] slot=%s receiver=%s conn_type=%s",
                    slot.__name__,
                    receiver,
                    actual_conn_type,
                )

                try:
                    if actual_conn_type == TConnectionType.DIRECT_CONNECTION:
                        logger.debug("[TSignal][emit][DIRECT] calling slot directly")
                        result = slot(*args, **kwargs)
                        logger.debug(
                            "[TSignal][emit][DIRECT] result=%s result_type=%s",
                            result,
                            type(result),
                        )
                    else:
                        # Handle QUEUED CONNECTION
                        if receiver is not None:
                            receiver_loop = getattr(
                                receiver, TSignalConstants.LOOP, None
                            )

                            receiver_thread = getattr(
                                receiver, TSignalConstants.THREAD, None
                            )
                            if not receiver_loop:
                                logger.error(
                                    "[TSignal][emit][QUEUED] No event loop found for receiver. receiver=%s",
                                    receiver,
                                    stack_info=True,
                                )
                                continue
                        else:
                            try:
                                receiver_loop = asyncio.get_running_loop()
                            except RuntimeError:
                                t_signal_log_and_raise_error(
                                    logger,
                                    RuntimeError,
                                    "[TSignal][emit][QUEUED] No running event loop found for queued connection.",
                                )

                            receiver_thread = None

                        if not receiver_loop.is_running():
                            logger.warning(
                                "[TSignal][emit][QUEUED] receiver loop not running. Signals may not be delivered. receiver=%s",
                                receiver.__class__.__name__,
                            )
                            continue

                        if receiver_thread and not receiver_thread.is_alive():
                            logger.warning(
                                "[TSignal][emit][QUEUED] The receiver's thread is not alive. Signals may not be delivered. receiver=%s",
                                receiver.__class__.__name__,
                            )

                        logger.debug(
                            "[TSignal][emit][QUEUED] slot=%s is_coroutine=%s",
                            slot.__name__,
                            is_coro_slot,
                        )

                        def dispatch(slot=slot, is_coro_slot=is_coro_slot):
                            logger.debug(
                                "[TSignal][emit][QUEUED][dispatch] calling slot=%s",
                                slot.__name__,
                            )

                            if is_coro_slot:
                                returned = asyncio.create_task(slot(*args, **kwargs))
                            else:
                                returned = slot(*args, **kwargs)

                            logger.debug(
                                "[TSignal][emit][QUEUED][dispatch] returned=%s type=%s",
                                returned,
                                type(returned),
                            )

                            return returned

                        receiver_loop.call_soon_threadsafe(dispatch)

                except Exception as e:
                    logger.error(
                        "[TSignal][emit] error in emission: %s", e, exc_info=True
                    )
        finally:
            _tsignal_from_emit.reset(token)

        logger.debug("[TSignal][emit][END]")


# property is used for lazy initialization of the signal.
# The signal object is created only when first accessed, and a cached object is returned thereafter.
class TSignalProperty(property):
    """Signal property class for tsignal."""

    def __init__(self, fget, signal_name):
        super().__init__(fget)
        self.signal_name = signal_name

    def __get__(self, obj, objtype=None):
        signal = super().__get__(obj, objtype)

        if obj is not None:
            signal.owner = obj

        return signal


def t_signal(func):
    """Signal decorator"""

    sig_name = func.__name__

    def wrap(self):
        """Wrap signal"""

        if not hasattr(self, f"_{sig_name}"):
            setattr(self, f"_{sig_name}", TSignal())
        return getattr(self, f"_{sig_name}")

    return TSignalProperty(wrap, sig_name)


def t_slot(func):
    """Slot decorator"""

    is_coroutine = asyncio.iscoroutinefunction(func)

    if is_coroutine:

        @functools.wraps(func)
        async def wrap(self, *args, **kwargs):
            """Wrap coroutine slots"""

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                t_signal_log_and_raise_error(
                    logger,
                    RuntimeError,
                    "[TSignal][t_slot][wrap] No running loop in coroutine.",
                )

            if not hasattr(self, TSignalConstants.THREAD):
                self._tsignal_thread = threading.current_thread()

            if not hasattr(self, TSignalConstants.LOOP):
                try:
                    self._tsignal_loop = asyncio.get_running_loop()
                except RuntimeError:
                    self._tsignal_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._tsignal_loop)

            if not _tsignal_from_emit.get():
                current_thread = threading.current_thread()

                if current_thread != self._tsignal_thread:
                    future = asyncio.run_coroutine_threadsafe(
                        func(self, *args, **kwargs), self._tsignal_loop
                    )
                    return await asyncio.wrap_future(future)

            return await func(self, *args, **kwargs)

    else:

        @functools.wraps(func)
        def wrap(self, *args, **kwargs):
            """Wrap regular slots"""

            if not hasattr(self, TSignalConstants.THREAD):
                self._tsignal_thread = threading.current_thread()

            if not hasattr(self, TSignalConstants.LOOP):
                try:
                    self._tsignal_loop = asyncio.get_running_loop()
                except RuntimeError:
                    t_signal_log_and_raise_error(
                        logger,
                        RuntimeError,
                        "[t_slot][wrap] No running event loop found.",
                    )

            if not _tsignal_from_emit.get():
                current_thread = threading.current_thread()

                if current_thread != self._tsignal_thread:
                    future = concurrent.futures.Future()

                    def callback():
                        """Callback function for thread-safe execution"""

                        try:
                            result = func(self, *args, **kwargs)
                            future.set_result(result)
                        except Exception as e:
                            future.set_exception(e)

                    self._tsignal_loop.call_soon_threadsafe(callback)
                    return future.result()

            return func(self, *args, **kwargs)

    return wrap


def t_with_signals(cls, *, loop=None):
    """Decorator for classes using signals"""

    def wrap(cls):
        """Wrap class with signals"""

        original_init = cls.__init__

        def __init__(self, *args, **kwargs):
            current_loop = loop

            if current_loop is None:
                try:
                    current_loop = asyncio.get_running_loop()
                except RuntimeError:
                    t_signal_log_and_raise_error(
                        logger,
                        RuntimeError,
                        "[t_with_signals][wrap][__init__] No running event loop found.",
                    )

            # Set thread and event loop
            self._tsignal_thread = threading.current_thread()
            self._tsignal_affinity = self._tsignal_thread
            self._tsignal_loop = current_loop

            # Call the original __init__
            original_init(self, *args, **kwargs)

        cls.__init__ = __init__
        return cls

    if cls is None:
        return wrap

    return wrap(cls)


async def t_signal_graceful_shutdown():
    """
    Waits for all pending tasks to complete.
    This repeatedly checks for tasks until none are left except the current one.
    """
    while True:
        await asyncio.sleep(0)  # Let the event loop process pending callbacks

        tasks = asyncio.all_tasks()
        tasks.discard(asyncio.current_task())

        if not tasks:
            break

        # Wait for all pending tasks to complete (or fail) before checking again
        await asyncio.gather(*tasks, return_exceptions=True)
