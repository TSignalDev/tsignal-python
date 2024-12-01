import asyncio
import threading
import logging
import time

logger = logging.getLogger(__name__)


def t_with_worker(cls):
    if not asyncio.iscoroutinefunction(getattr(cls, "initialize", None)):
        raise TypeError(f"{cls.__name__}.initialize must be an async function")
    if not asyncio.iscoroutinefunction(getattr(cls, "finalize", None)):
        raise TypeError(f"{cls.__name__}.finalize must be an async function")

    class WorkerClass(cls):
        def __init__(self):
            self._worker_loop = None
            self._worker_thread = None
            self._stopping = asyncio.Event()
            self._task_queue = asyncio.Queue()
            # Setting up thread/loop for compatibility with t_with_signals
            self._thread = threading.current_thread()
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            super().__init__()

        async def queue_task(self, coro):
            """Method to add a task to the queue"""
            await self._task_queue.put(coro)

        async def _process_queue(self):
            """Internal method to process the task queue"""
            while not self._stopping.is_set():
                try:
                    coro = await asyncio.wait_for(self._task_queue.get(), timeout=0.1)
                    await coro
                    self._task_queue.task_done()
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing queued task: {e}")

        def start(self, *args, **kwargs):
            if self._worker_thread:
                raise RuntimeError("Worker already started")

            def run():
                self._worker_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._worker_loop)
                self._thread = threading.current_thread()
                self._loop = self._worker_loop
                try:
                    self._worker_loop.run_until_complete(
                        self.initialize(*args, **kwargs)
                    )

                    async def run_loop():
                        try:
                            queue_task = self._worker_loop.create_task(
                                self._process_queue()
                            )

                            await self._stopping.wait()

                            queue_task.cancel()
                            try:
                                await queue_task
                            except asyncio.CancelledError:
                                pass

                            if hasattr(self, "finalize"):
                                await self.finalize()

                                initial_pending = [
                                    task
                                    for task in asyncio.all_tasks(self._worker_loop)
                                    if task is not asyncio.current_task()
                                ]

                                # Wait until all callbacks in the current event loop are processed
                                while self._worker_loop.is_running():
                                    pending_tasks = [
                                        task
                                        for task in asyncio.all_tasks(self._worker_loop)
                                        if task is not asyncio.current_task()
                                    ]
                                    if not pending_tasks:
                                        break

                                    await asyncio.gather(
                                        *pending_tasks, return_exceptions=True
                                    )

                        finally:
                            if self._worker_loop and self._worker_loop.is_running():
                                self._worker_loop.stop()

                    self._worker_loop.create_task(run_loop())
                    self._worker_loop.run_forever()
                finally:
                    if self._worker_loop:
                        self._worker_loop.close()
                        self._worker_loop = None

            self._worker_thread = threading.Thread(
                target=run, name=f"{cls.__name__}Worker", daemon=True
            )
            self._worker_thread.start()

        def stop(self):
            if (
                self._worker_loop
                and self._worker_thread
                and self._worker_thread.is_alive()
            ):
                self._worker_loop.call_soon_threadsafe(self._stopping.set)
                self._worker_thread.join(timeout=1)

                if self._worker_thread and self._worker_thread.is_alive():
                    logger.warning(
                        f"Worker thread {self._worker_thread.name} did not stop gracefully"
                    )
                    self._worker_thread = None

    return WorkerClass
