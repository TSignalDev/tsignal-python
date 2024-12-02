import pytest
import asyncio
import logging
from tsignal.contrib.patterns.worker.decorators import t_with_worker

logger = logging.getLogger(__name__)


@pytest.fixture
async def queue_worker():
    logger.info("Creating QueueWorker")
    w = QueueWorker()
    yield w
    logger.info("Cleaning up QueueWorker")
    if getattr(w, "_worker_thread", None) and w._worker_thread.is_alive():
        w.stop()
        w._worker_thread.join(timeout=1)


@t_with_worker
class QueueWorker:
    def __init__(self):
        self.processed_items = []
        super().__init__()

    async def initialize(self):
        logger.info("QueueWorker initializing")

    async def finalize(self):
        logger.info("QueueWorker finalizing")

    async def process_item(self, item):
        logger.info(f"Processing item: {item}")
        await asyncio.sleep(0.1)  # Simulate work
        self.processed_items.append(item)


@pytest.mark.asyncio
async def test_basic_queue_operation(queue_worker):
    """Basic queue operation test"""
    queue_worker.start()
    await asyncio.sleep(0.1)

    await queue_worker.queue_task(queue_worker.process_item("item1"))
    await queue_worker.queue_task(queue_worker.process_item("item2"))

    await asyncio.sleep(0.5)

    assert "item1" in queue_worker.processed_items
    assert "item2" in queue_worker.processed_items
    assert len(queue_worker.processed_items) == 2


@pytest.mark.asyncio
async def test_queue_order(queue_worker):
    """Test for ensuring the order of the task queue"""
    queue_worker.start()
    await asyncio.sleep(0.1)

    items = ["first", "second", "third"]
    for item in items:
        await queue_worker.queue_task(queue_worker.process_item(item))

    await asyncio.sleep(0.5)

    assert queue_worker.processed_items == items


@pytest.mark.asyncio
async def test_queue_error_handling(queue_worker):
    """Test for error handling in the task queue"""

    async def failing_task():
        raise ValueError("Test error")

    queue_worker.start()
    await asyncio.sleep(0.1)

    # Add normal and failing tasks
    await queue_worker.queue_task(queue_worker.process_item("good_item"))
    await queue_worker.queue_task(failing_task())
    await queue_worker.queue_task(queue_worker.process_item("after_error"))

    await asyncio.sleep(0.5)

    # The error should not prevent the next task from being processed
    assert "good_item" in queue_worker.processed_items
    assert "after_error" in queue_worker.processed_items


@pytest.mark.asyncio
async def test_queue_cleanup_on_stop(queue_worker):
    """Test for queue cleanup when worker stops"""
    queue_worker.start()
    await asyncio.sleep(0.1)

    # Add a long task
    async def long_task():
        await asyncio.sleep(0.5)
        queue_worker.processed_items.append("long_task")

    await queue_worker.queue_task(long_task())
    await asyncio.sleep(0.1)  # Wait for the task to start

    # Stop the worker while the task is running
    queue_worker.stop()

    # Check if the worker exited normally
    assert not queue_worker._worker_thread.is_alive()


@pytest.mark.asyncio
async def test_mixed_signal_and_queue(queue_worker):
    """Test for simultaneous use of signals and task queue"""
    from tsignal import t_signal

    # Add a signal
    @t_signal
    def task_completed(self):
        pass

    queue_worker.task_completed = task_completed.__get__(queue_worker)
    signal_received = []
    queue_worker.task_completed.connect(lambda: signal_received.append(True))

    queue_worker.start()
    await asyncio.sleep(0.1)

    # Add a task and emit the signal
    async def task_with_signal():
        await asyncio.sleep(0.1)
        queue_worker.processed_items.append("signal_task")
        queue_worker.task_completed.emit()

    await queue_worker.queue_task(task_with_signal())
    await asyncio.sleep(0.3)

    assert "signal_task" in queue_worker.processed_items
    assert signal_received == [True]
