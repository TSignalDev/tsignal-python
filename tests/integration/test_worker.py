# tests/integration/test_worker.py

"""
Test cases for the worker pattern.
"""

# pylint: disable=no-member
# pylint: disable=redefined-outer-name
# pylint: disable=unused-variable

import asyncio
import logging
import pytest
from tsignal.contrib.patterns.worker.decorators import t_with_worker
from tsignal.core import TSignalConstants

logger = logging.getLogger(__name__)


@pytest.fixture
async def worker():
    """Create a worker"""
    logger.info("[TestWorker][fixture] Creating worker in fixture")
    w = TestWorker()
    yield w
    logger.info("[TestWorker][fixture] Cleaning up worker in fixture")
    if getattr(w, TSignalConstants.THREAD, None) and w._tsignal_thread.is_alive():
        logger.info("[TestWorker][fixture] Stopping worker thread")
        w.stop()
        logger.info("[TestWorker][fixture] Stopping worker thread complete")


@t_with_worker
class TestWorker:
    """Test worker class"""

    def __init__(self):
        logger.info("[TestWorker][__init__]")
        self.run_called = False
        self.data = []
        super().__init__()

    async def run(self, *args, **kwargs):
        """Run the worker"""
        logger.info("[TestWorker][run] called with %s, %s", args, kwargs)
        self.run_called = True
        initial_value = args[0] if args else kwargs.get("initial_value", None)
        if initial_value:
            self.data.append(initial_value)
        await self.start_queue()


@pytest.mark.asyncio
async def test_worker_lifecycle(worker):
    """Test the worker lifecycle"""
    logger.info("Starting test_worker_lifecycle")
    initial_value = "test"

    logger.info("Checking initial state")
    assert worker._tsignal_thread is None
    assert worker._tsignal_loop is None
    assert not worker.run_called

    logger.info("Starting worker")
    worker.start(initial_value)

    logger.info("Waiting for worker initialization")
    for i in range(10):
        if worker.run_called:
            logger.info("Worker run called after %d attempts", i + 1)
            break
        logger.info("Waiting attempt %d", i + 1)
        await asyncio.sleep(0.1)
    else:
        logger.error("Worker failed to run")
        pytest.fail("Worker did not run in time")

    logger.info("Checking worker state")
    assert worker.run_called
    assert worker.data == [initial_value]

    logger.info("Stopping worker")
    worker.stop()
