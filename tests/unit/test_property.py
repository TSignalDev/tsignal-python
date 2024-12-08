import pytest
import asyncio
import threading
from tsignal.contrib.extensions.property import t_property
from tsignal import t_signal, t_with_signals
import logging


logger = logging.getLogger(__name__)


@t_with_signals
class Temperature:
    def __init__(self):
        super().__init__()
        self._celsius = -273

    @t_signal
    def celsius_changed(self):
        pass

    @t_property(notify=celsius_changed)
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float):
        self._celsius = value


@t_with_signals
class ReadOnlyTemperature:
    def __init__(self):
        super().__init__()
        self._celsius = 0

    @t_signal
    def celsius_changed(self):
        pass

    @t_property(notify=celsius_changed)
    def celsius(self) -> float:
        return self._celsius


def test_property_basic():
    """Test basic property get/set operations"""
    temp = Temperature()
    assert temp.celsius == -273

    # Test setter
    temp.celsius = 25
    assert temp.celsius == 25


def test_property_notification():
    """Test property change notifications"""
    temp = Temperature()
    received_values = []

    # Connect signal
    temp.celsius_changed.connect(lambda x: received_values.append(x))

    # Test initial value
    temp.celsius = 25
    assert temp.celsius == 25
    assert received_values == [25]

    # Clear received values
    received_values.clear()

    # Test no notification on same value
    temp.celsius = 25
    assert not received_values

    # Test notification on value change
    temp.celsius = 30
    assert received_values == [30]

    # Test multiple changes
    temp.celsius = 15
    temp.celsius = 45
    assert received_values == [30, 15, 45]


def test_property_read_only():
    """Test read-only property behavior"""
    temp = ReadOnlyTemperature()

    with pytest.raises(AttributeError, match="can't set attribute"):
        temp.celsius = 25


@pytest.mark.asyncio
async def test_property_thread_safety():
    """Test property thread safety and notifications across threads"""
    temp = Temperature()
    received_values = []
    logger.debug(f"test_property_thread_safety #3")
    task_completed = asyncio.Event()
    logger.debug(f"test_property_thread_safety #4")
    main_loop = asyncio.get_running_loop()

    def background_task():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def set_temp():
            temp.celsius = 15
            await asyncio.sleep(0.1)

        try:
            loop.run_until_complete(set_temp())
        finally:
            loop.close()
            main_loop.call_soon_threadsafe(task_completed.set)

    # Connect signal
    temp.celsius_changed.connect(lambda x: received_values.append(x))

    # Start background thread
    thread = threading.Thread(target=background_task)
    thread.start()

    # asyncio.Event의 wait() 사용
    await task_completed.wait()

    thread.join()

    assert temp.celsius == 15
    assert 15 in received_values


@pytest.mark.asyncio
async def test_property_multiple_threads():
    """Test property behavior with multiple threads"""
    temp = Temperature()
    received_values = []
    values_lock = threading.Lock()
    threads_lock = threading.Lock()
    NUM_THREADS = 5
    task_completed = asyncio.Event()
    threads_done = 0
    main_loop = asyncio.get_running_loop()

    def on_celsius_changed(value):
        with values_lock:
            received_values.append(value)

    temp.celsius_changed.connect(on_celsius_changed)

    def background_task(value):
        nonlocal threads_done
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with threads_lock:
                temp.celsius = value
                loop.run_until_complete(asyncio.sleep(0.1))
        finally:
            loop.close()

            with threading.Lock():
                nonlocal threads_done
                threads_done += 1
                if threads_done == NUM_THREADS:
                    main_loop.call_soon_threadsafe(task_completed.set)

    threads = [
        threading.Thread(target=background_task, args=(i * 10,))
        for i in range(NUM_THREADS)
    ]

    logger.debug("Starting threads")
    for thread in threads:
        thread.start()

    logger.debug("Waiting for task_completed event")
    try:
        await asyncio.wait_for(task_completed.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for threads")

    logger.debug("Joining threads")
    for thread in threads:
        thread.join()

    await asyncio.sleep(0.2)

    expected_values = set(i * 10 for i in range(NUM_THREADS))
    received_set = set(received_values)

    assert (
        expected_values == received_set
    ), f"Expected {expected_values}, got {received_set}"

    # DEBUG: Connect debug handler to monitor value changes
    # temp.celsius_changed.connect(
    #     lambda x: logger.debug(f"Temperature value after change: {temp.celsius}")
    # )


def test_property_exception_handling():
    """Test property behavior with exceptions in signal handlers"""
    temp = Temperature()
    received_values = []

    def handler_with_exception(value):
        received_values.append(value)
        raise ValueError("Test exception")

    def normal_handler(value):
        received_values.append(value * 2)

    # Connect multiple handlers
    temp.celsius_changed.connect(handler_with_exception)
    temp.celsius_changed.connect(normal_handler)

    # Exception in handler shouldn't prevent property update
    temp.celsius = 25

    assert temp.celsius == 25
    assert 25 in received_values  # First handler executed
    assert 50 in received_values  # Second handler executed
