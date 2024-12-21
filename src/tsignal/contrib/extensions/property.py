# src/tsignal/contrib/extensions/property.py

# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
# pylint: disable=no-else-return
# pylint: disable=unnecessary-dunder-call

"""
This module provides a property decorator that allows for thread-safe access to properties.
"""

import asyncio
import threading
import logging
from tsignal.core import TSignalConstants
from tsignal.utils import t_signal_log_and_raise_error

logger = logging.getLogger(__name__)


class TProperty(property):
    """
    A thread-safe property decorator for classes decorated with `@t_with_signals`
    or `@t_with_worker`.

    This property ensures that all reads (getter) and writes (setter) occur on the
    object's designated event loop, maintaining thread-safety across different threads.

    If the property is accessed from a different thread than the object's thread affinity:
    - The operation is automatically dispatched (queued) onto the object's event loop
      via `asyncio.run_coroutine_threadsafe`.
    - This prevents race conditions that might otherwise occur if multiple threads
      tried to read/write the same attribute.

    Parameters
    ----------
    fget : callable, optional
        The getter function for the property.
    fset : callable, optional
        The setter function for the property.
    fdel : callable, optional
        The deleter function for the property (not commonly used).
    doc : str, optional
        Docstring for this property.
    notify : TSignal, optional
        A signal to emit when the property value changes. If provided, the signal is
        triggered after a successful write operation, and only if the new value is
        different from the old value.

    Notes
    -----
    - The property’s underlying storage is typically `_private_name` on the instance,
      inferred from the property name (e.g. `value` -> `self._value`).
    - If `notify` is set, `signal.emit(new_value)` is called whenever the property changes.
    - Reading or writing this property from its "home" thread is done synchronously;
      from any other thread, TSignal automatically queues the operation in the
      object's event loop.

    Example
    -------
    @t_with_signals
    class Model:
        @t_signal
        def value_changed(self):
            pass

        @t_property(notify=value_changed)
        def value(self):
            return self._value

        @value.setter
        def value(self, new_val):
            self._value = new_val

    # Usage:
    model = Model()
    model.value = 10     # If called from a different thread, it’s queued to model's loop
    current_val = model.value  # Also thread-safe read

    See Also
    --------
    t_with_signals : Decorates a class to enable signal/slot features and thread affinity.
    """

    def __init__(self, fget=None, fset=None, fdel=None, doc=None, notify=None):
        super().__init__(fget, fset, fdel, doc)
        self.notify = notify
        self._private_name = None

    def __set_name__(self, owner, name):
        self._private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.fget is None:
            raise AttributeError("unreadable attribute")

        if (
            hasattr(obj, TSignalConstants.THREAD)
            and threading.current_thread() != obj._tsignal_thread
        ):
            # Dispatch to event loop when accessed from a different thread
            future = asyncio.run_coroutine_threadsafe(
                self._get_value(obj), obj._tsignal_loop
            )
            return future.result()
        else:
            return self._get_value_sync(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")

        # DEBUG: Thread safety verification logs
        # logger.debug(f"[PROPERTY] thread: {obj._tsignal_thread} current thread: {threading.current_thread()} loop: {obj._tsignal_loop}")

        if (
            hasattr(obj, TSignalConstants.THREAD)
            and threading.current_thread() != obj._tsignal_thread
        ):
            # Queue the setter call in the object's event loop
            future = asyncio.run_coroutine_threadsafe(
                self._set_value(obj, value), obj._tsignal_loop
            )
            # Wait for completion like slot direct calls
            return future.result()
        else:
            return self._set_value_sync(obj, value)

    def _set_value_sync(self, obj, value):
        old_value = self.__get__(obj, type(obj))
        result = self.fset(obj, value)

        if self.notify is not None and old_value != value:
            try:
                signal_name = getattr(self.notify, "signal_name", None)

                if signal_name:
                    signal = getattr(obj, signal_name)
                    signal.emit(value)
                else:
                    t_signal_log_and_raise_error(
                        logger, AttributeError, f"No signal_name found in {self.notify}"
                    )

            except AttributeError as e:
                logger.warning(
                    "Property %s notify attribute not found. Error: %s",
                    self._private_name,
                    str(e),
                )

        return result

    async def _set_value(self, obj, value):
        return self._set_value_sync(obj, value)

    def _get_value_sync(self, obj):
        return self.fget(obj)

    async def _get_value(self, obj):
        return self._get_value_sync(obj)

    def setter(self, fset):
        """
        Set the setter for the property.
        """
        return type(self)(self.fget, fset, self.fdel, self.__doc__, self.notify)


def t_property(notify=None):
    """
    Decorator to create a TProperty-based thread-safe property.

    Parameters
    ----------
    notify : TSignal, optional
        If provided, this signal is automatically emitted when the property's value changes.

    Returns
    -------
    function
        A decorator that converts a normal getter function into a TProperty-based property.

    Example
    -------
    @t_with_signals
    class Example:
        @t_signal
        def updated(self):
            pass

        @t_property(notify=updated)
        def data(self):
            return self._data

        @data.setter
        def data(self, value):
            self._data = value

    e = Example()
    e.data = 42  # Thread-safe property set; emits 'updated' signal on change
    """

    def decorator(func):
        return TProperty(fget=func, notify=notify)

    return decorator
