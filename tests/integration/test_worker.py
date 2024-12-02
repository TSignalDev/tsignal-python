import pytest
import asyncio
import threading
import logging
from tsignal.contrib.patterns.worker.decorators import t_with_worker

logger = logging.getLogger(__name__)


@pytest.fixture
async def worker():
    logger.info("Creating worker in fixture")
    w = TestWorker()
    yield w
    logger.info("Cleaning up worker in fixture")
    if getattr(w, "_worker_thread", None) and w._worker_thread.is_alive():
        logger.info("Stopping worker thread")
        w.stop()
        logger.info("Waiting for worker thread to join")
        w._worker_thread.join(timeout=1)
        logger.info("Worker thread cleanup complete")


@t_with_worker
class TestWorker:
    def __init__(self):
        logger.info("Initializing TestWorker")
        self.initialize_called = False
        self.finalize_called = False
        self.data = []
        super().__init__()

    async def initialize(self, initial_value=None):
        logger.info(f"TestWorker.initialize called with {initial_value}")
        self.initialize_called = True
        if initial_value:
            self.data.append(initial_value)

    async def finalize(self):
        logger.info("TestWorker.finalize called")
        self.finalize_called = True


def test_worker_requires_async_methods():
    logger.info("Starting test_worker_requires_async_methods")
    with pytest.raises(TypeError, match=r".*initialize must be an async function"):

        @t_with_worker
        class InvalidWorker1:
            def initialize(self):  # not async
                pass

            async def finalize(self):
                pass

    logger.info("First check passed")

    with pytest.raises(TypeError, match=r".*finalize must be an async function"):

        @t_with_worker
        class InvalidWorker2:
            async def initialize(self):
                pass

            def finalize(self):  # not async
                pass

    logger.info("Second check passed")


@pytest.mark.asyncio
async def test_worker_lifecycle(worker):
    logger.info("Starting test_worker_lifecycle")
    initial_value = "test"

    logger.info("Checking initial state")
    assert worker._worker_thread is None
    assert worker._worker_loop is None
    assert not worker.initialize_called
    assert not worker.finalize_called

    logger.info("Starting worker")
    worker.start(initial_value)

    logger.info("Waiting for worker initialization")
    for i in range(10):
        if worker.initialize_called:
            logger.info(f"Worker initialized after {i+1} attempts")
            break
        logger.info(f"Waiting attempt {i+1}")
        await asyncio.sleep(0.1)
    else:
        logger.error("Worker failed to initialize")
        pytest.fail("Worker did not initialize in time")

    logger.info("Checking worker state")
    assert worker.initialize_called
    assert worker.data == [initial_value]

    logger.info("Stopping worker")
    worker.stop()

    logger.info("Checking final state")
    assert worker.finalize_called
    logger.info("Test complete")
