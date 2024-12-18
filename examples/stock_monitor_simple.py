# examples/05_stock_monitor_simple_updated.py

"""
Stock monitor simple example.
"""

# pylint: disable=no-member
# pylint: disable=unused-argument

import asyncio
import logging
import threading
import time
from utils import logger_setup
from tsignal import t_with_signals, t_signal, t_slot, t_with_worker

logger_setup("tsignal", level=logging.DEBUG)
logger = logger_setup(__name__, level=logging.DEBUG)


@t_with_worker
class DataWorker:
    """Data worker"""

    def __init__(self):
        self._running = False
        self._update_task = None

    @t_signal
    def data_processed(self):
        """Signal emitted when data is processed"""

    async def run(self, *args, **kwargs):
        """Worker initialization"""

        logger.info("[DataWorker][run] Starting")

        self._running = True
        self._update_task = asyncio.create_task(self.update_loop())
        # Wait until run() is finished
        await self._tsignal_stopping.wait()
        # Clean up
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

    async def update_loop(self):
        """Update loop"""

        count = 0
        while self._running:
            logger.debug("[Worker] Processing data %d", count)
            self.data_processed.emit(count)
            count += 1
            await asyncio.sleep(1)


@t_with_signals
class DataDisplay:
    """Data display"""

    def __init__(self):
        self.last_value = None
        logger.debug("[Display] Created in thread: %s", threading.current_thread().name)

    @t_slot
    def on_data_processed(self, value):
        """Slot called when data is processed"""

        current_thread = threading.current_thread()
        logger.debug(
            "[Display] Received value %d in thread: %s", value, current_thread.name
        )
        self.last_value = value
        # Add a small delay to check the result
        time.sleep(0.1)
        logger.debug("[Display] Processed value %d", value)


async def main():
    """Main function"""

    logger.debug("[Main] Starting in thread: %s", threading.current_thread().name)

    worker = DataWorker()
    display = DataDisplay()

    # Both are in the main thread at the connection point
    worker.data_processed.connect(display, display.on_data_processed)

    worker.start()

    try:
        await asyncio.sleep(3)  # Run for 3 seconds
    finally:
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
