import pytest
import asyncio
import threading
from tsignal import t_with_signals, t_signal, t_slot
import logging
import sys
import os

# Only creating the logger without configuration
logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@t_with_signals
class Sender:
    @t_signal
    def value_changed(self, value):
        """Signal for value changes"""
        pass

    def emit_value(self, value):
        self.value_changed.emit(value)


@t_with_signals
class Receiver:
    def __init__(self):
        super().__init__()
        self.received_value = None
        self.received_count = 0
        self.id = id(self)
        logger.info(f"Created Receiver[{self.id}]")

    @t_slot
    async def on_value_changed(self, value: int):
        logger.info(f"Receiver[{self.id}] on_value_changed called with value: {value}")
        logger.info(f"Current thread: {threading.current_thread().name}")
        logger.info(f"Current event loop: {asyncio.get_running_loop()}")
        self.received_value = value
        self.received_count += 1
        logger.info(
            f"Receiver[{self.id}] updated: value={self.received_value}, count={self.received_count}"
        )

    @t_slot
    def on_value_changed_sync(self, value: int):
        print(f"Receiver[{self.id}] received value (sync): {value}")
        self.received_value = value
        self.received_count += 1
        print(
            f"Receiver[{self.id}] updated (sync): value={self.received_value}, count={self.received_count}"
        )


@pytest.fixture
def receiver(event_loop):
    return Receiver()


@pytest.fixture
def sender(event_loop):
    return Sender()


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Configure logging for tests"""
    # Setting up the root logger
    root = logging.getLogger()

    # Setting to WARNING level by default
    default_level = logging.WARNING

    # Can enable DEBUG mode via environment variable
    if os.environ.get("TSIGNAL_DEBUG"):
        default_level = logging.DEBUG

    root.setLevel(default_level)

    # Removing existing handlers
    for handler in root.handlers:
        root.removeHandler(handler)

    # Setting up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(default_level)

    # Setting formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # Setting package logger levels
    logging.getLogger("tsignal").setLevel(default_level)
    logging.getLogger("tests").setLevel(default_level)
