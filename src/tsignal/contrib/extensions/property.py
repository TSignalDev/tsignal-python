import asyncio
import threading
import logging
from tsignal.core import TSignalConstants

# Initialize logger

logger = logging.getLogger(__name__)


class TProperty(property):
    def __init__(self, fget=None, fset=None, fdel=None, doc=None, notify=None):
        super().__init__(fget, fset, fdel, doc)
        self.notify = notify
        self._private_name = None

    def __set_name__(self, owner, name):
        self._private_name = f"_{name}"

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")

        # DEBUG: Thread safety verification logs
        # logger.debug(f"Object thread: {obj._thread}")
        # logger.debug(f"Current thread: {threading.current_thread()}")
        # logger.debug(f"Object loop: {obj._loop}")

        if (
            hasattr(obj, TSignalConstants.THREAD)
            and threading.current_thread() != obj._thread
        ):
            # Queue the setter call in the object's event loop
            future = asyncio.run_coroutine_threadsafe(
                self._set_value(obj, value), obj._loop
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
                    raise AttributeError(f"No signal_name found in {self.notify}")

            except AttributeError as e:
                logger.warning(
                    f"Property {self._private_name} notify attribute not found. Error: {str(e)}"
                )
                pass

        return result

    async def _set_value(self, obj, value):
        return self._set_value_sync(obj, value)

    def setter(self, fset):
        return type(self)(self.fget, fset, self.fdel, self.__doc__, self.notify)


def t_property(notify=None):
    logger.debug(f"t_property: {notify}")

    def decorator(func):
        return TProperty(fget=func, notify=notify)

    return decorator
