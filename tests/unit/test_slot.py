"""
Test cases for the slot pattern.
"""

import asyncio
import threading
import time
import pytest
from tsignal import t_with_signals, t_slot
import logging

logger = logging.getLogger(__name__)


def test_sync_slot(sender, receiver):
    """Test synchronous slot execution"""
    sender.value_changed.connect(receiver, receiver.on_value_changed_sync)
    sender.emit_value(42)
    assert receiver.received_value == 42
    assert receiver.received_count == 1


@pytest.mark.asyncio
async def test_directly_call_slot(receiver):
    """Test direct slot calls"""
    await receiver.on_value_changed(42)
    assert receiver.received_value == 42
    assert receiver.received_count == 1

    receiver.on_value_changed_sync(43)
    assert receiver.received_value == 43
    assert receiver.received_count == 2


def test_slot_exception(sender, receiver, event_loop):
    """Test exception handling in slots"""

    @t_with_signals
    class ExceptionReceiver:
        """Receiver class for exception testing"""

        @t_slot
        async def on_value_changed(self, value):
            """Slot for value changed"""
            raise ValueError("Test exception")

    exception_receiver = ExceptionReceiver()
    sender.value_changed.connect(
        exception_receiver, exception_receiver.on_value_changed
    )
    sender.value_changed.connect(receiver, receiver.on_value_changed)

    async def test():
        sender.emit_value(42)
        await asyncio.sleep(0.1)
        assert receiver.received_value == 42
        assert receiver.received_count == 1

    event_loop.run_until_complete(test())


@pytest.mark.asyncio
async def test_slot_thread_safety():
    """Test slot direct calls from different threads"""

    @t_with_signals
    class ThreadTestReceiver:
        def __init__(self):
            super().__init__()
            self.received_value = None
            self.received_count = 0
            self.execution_thread = None

        @t_slot
        async def async_slot(self, value):
            self.execution_thread = threading.current_thread()
            await asyncio.sleep(0.1)  # work simulation with sleep
            self.received_value = value
            self.received_count += 1

        @t_slot
        def sync_slot(self, value):
            self.execution_thread = threading.current_thread()
            time.sleep(0.1)  # work simulation with sleep
            self.received_value = value
            self.received_count += 1

    receiver = ThreadTestReceiver()
    task_completed = threading.Event()
    main_thread = threading.current_thread()
    initial_values = {"value": None, "count": 0}  # save initial values

    def background_task():
        try:
            # Before async_slot call
            initial_values["value"] = receiver.received_value
            initial_values["count"] = receiver.received_count

            coro = receiver.async_slot(42)
            future = asyncio.run_coroutine_threadsafe(coro, receiver._loop)
            # Wait for async_slot result
            future.result()

            # verify state change
            assert receiver.received_value != initial_values["value"]
            assert receiver.received_count == initial_values["count"] + 1
            assert receiver.execution_thread == main_thread

            # Before sync_slot call
            initial_values["value"] = receiver.received_value
            initial_values["count"] = receiver.received_count

            receiver.sync_slot(43)

            # verify state change
            assert receiver.received_value != initial_values["value"]
            assert receiver.received_count == initial_values["count"] + 1
            assert receiver.execution_thread == main_thread

        finally:
            task_completed.set()

    async def run_test():
        thread = threading.Thread(target=background_task)
        thread.start()

        while not task_completed.is_set():
            await asyncio.sleep(0.1)

        thread.join()

        # Cleanup
        pending = asyncio.all_tasks(receiver._loop)
        if pending:
            logger.debug(f"Cleaning up {len(pending)} pending tasks")
            for task in pending:
                if "test_slot_thread_safety" in str(task.get_coro()):
                    logger.debug(f"Skipping test function task: {task}")
                else:
                    logger.debug(f"Found application task: {task}")
                    try:
                        await asyncio.gather(task, return_exceptions=True)
                    except Exception as e:
                        logger.error(f"Error during cleanup: {e}")
        else:
            logger.debug("No pending tasks to clean up")

    try:
        await run_test()
    except Exception as e:
        logger.error(f"Error in test: {e}")
