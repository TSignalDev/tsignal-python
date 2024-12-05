"""
Test cases for the worker-signal pattern.
"""

# pylint: disable=redefined-outer-name
# pylint: disable=unnecessary-lambda
# pylint: disable=unnecessary-lambda-assignment
# pylint: disable=no-member

import asyncio
import logging
import pytest
from tsignal.contrib.patterns.worker.decorators import t_with_worker
from tsignal import t_signal

logger = logging.getLogger(__name__)


@pytest.fixture
async def signal_worker():
    """Create a signal worker"""
    logger.info("Creating SignalWorker")
    w = SignalWorker()
    yield w
    logger.info("Cleaning up SignalWorker")
    if getattr(w, "_worker_thread", None) and w._worker_thread.is_alive():
        w.stop()
        w._worker_thread.join(timeout=1)


@t_with_worker
class SignalWorker:
    """Signal worker class"""

    def __init__(self):
        self.value = None
        super().__init__()

    @t_signal
    def value_changed(self):
        """Signal emitted when the value changes"""

    @t_signal
    def worker_event(self):
        """Signal emitted when a worker event occurs"""

    async def initialize(self):
        """Initialize the worker"""
        logger.info("SignalWorker initializing")
        self.value_changed.emit("initialized")

    async def finalize(self):
        """Finalize the worker"""
        logger.info("SignalWorker finalizing")
        self.value_changed.emit("finalized")

    def set_value(self, value):
        """Set the value and emit the signal"""
        logger.info("Setting value to: %s", value)
        self.value = value
        self.value_changed.emit(value)


@pytest.mark.asyncio
async def test_signal_from_initialize(signal_worker):
    """Test if the signal emitted from initialize is processed correctly"""
    received = []
    signal_worker.value_changed.connect(lambda v: received.append(v))

    signal_worker.start()
    await asyncio.sleep(0.1)

    assert "initialized" in received


@pytest.mark.asyncio
async def test_signal_from_finalize(signal_worker):
    """Test if the signal emitted from finalize is processed correctly"""
    received = []
    signal_worker.value_changed.connect(lambda v: received.append(v))

    signal_worker.start()
    await asyncio.sleep(0.1)
    signal_worker.stop()

    assert "finalized" in received


@pytest.mark.asyncio
async def test_signal_from_worker_thread(signal_worker):
    """Test if the signal emitted from the worker thread is processed correctly"""
    received = []
    signal_worker.value_changed.connect(lambda v: received.append(v))

    signal_worker.start()
    await asyncio.sleep(0.1)

    # Emit signal from the worker thread's event loop
    signal_worker._worker_loop.call_soon_threadsafe(
        lambda: signal_worker.set_value("test_value")
    )

    await asyncio.sleep(0.1)
    assert "test_value" in received


@pytest.mark.asyncio
async def test_multiple_signals(signal_worker):
    """Test if multiple signals are processed independently"""
    value_changes = []
    worker_events = []

    signal_worker.value_changed.connect(lambda v: value_changes.append(v))
    signal_worker.worker_event.connect(lambda v: worker_events.append(v))

    signal_worker.start()
    await asyncio.sleep(0.1)

    # Emit value_changed signal
    signal_worker._worker_loop.call_soon_threadsafe(
        lambda: signal_worker.set_value("test_value")
    )

    # Emit worker_event signal
    signal_worker._worker_loop.call_soon_threadsafe(
        lambda: signal_worker.worker_event.emit("worker_event")
    )

    await asyncio.sleep(0.1)

    assert "test_value" in value_changes
    assert "worker_event" in worker_events
    assert len(worker_events) == 1


@pytest.mark.asyncio
async def test_signal_disconnect(signal_worker):
    """Test if signal disconnection works correctly"""
    received = []
    handler = lambda v: received.append(v)

    signal_worker.value_changed.connect(handler)
    signal_worker.start()
    await asyncio.sleep(0.1)

    assert "initialized" in received
    received.clear()

    # Disconnect signal
    signal_worker.value_changed.disconnect(slot=handler)

    signal_worker._worker_loop.call_soon_threadsafe(
        lambda: signal_worker.set_value("after_disconnect")
    )

    await asyncio.sleep(0.1)
    assert len(received) == 0
