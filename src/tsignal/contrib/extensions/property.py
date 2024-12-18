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
    A thread-safe property decorator.
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
    Decorator to create a thread-safe property.
    """

    def decorator(func):
        return TProperty(fget=func, notify=notify)

    return decorator