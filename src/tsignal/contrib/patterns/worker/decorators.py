# src/tsignal/contrib/patterns/worker/decorators.py

# pylint: disable=not-callable

"""
Decorator for the worker pattern.

This decorator enhances a class to support a worker pattern, allowing for
asynchronous task processing in a separate thread. It ensures that the
class has the required asynchronous `initialize` and `finalize` methods,
facilitating the management of worker threads and task queues.
"""

import asyncio
import inspect
import logging
import threading
from tsignal.core import t_signal

logger = logging.getLogger(__name__)


class _WorkerConstants:
    """Constants for the worker pattern."""

    RUN_CORO = "run_coro"
    RUN = "run"


def t_with_worker(cls):
    """
    Class decorator that adds a worker pattern to the decorated class, allowing it
    to run in a dedicated thread with its own asyncio event loop. This is especially
    useful for background processing or offloading tasks that should not block the
    main thread.

    Features
    --------
    - **Dedicated Thread & Event Loop**: The decorated class, once started, runs in
      a new thread with its own event loop.
    - **Signal/Slot Support**: The worker class can define signals (with `@t_signal`)
      and slots (`@t_slot`), enabling event-driven communication.
    - **Task Queue**: A built-in asyncio `Queue` is provided for scheduling coroutines
      in the worker thread via `queue_task(coro)`.
    - **Lifecycle Signals**: Automatically emits `started` and `stopped` signals,
      indicating when the worker thread is up and when it has fully terminated.
    - **Lifecycle Management**: Methods like `start(...)`, `stop()`, and `move_to_thread(...)`
      help manage the worker thread's lifecycle and move other `@t_with_signals` objects
      into this worker thread.

    Usage
    -----
    1. Decorate the class with `@t_with_worker`.
    2. Optionally implement an async `run(*args, **kwargs)` method to control
       the worker's main logic. This method is run in the worker thread.
    3. Call `start(...)` to launch the thread and event loop.
    4. Use `queue_task(...)` to schedule coroutines on the worker's event loop.

    Example
    -------
    @t_with_worker
    class BackgroundWorker:
        @t_signal
        def started(self):
            pass

        @t_signal
        def stopped(self):
            pass

        @t_signal
        def result_ready(self):
            pass

        async def run(self, config=None):
            print("Worker started with config:", config)
            # Wait until stop is requested
            await self.wait_for_stop()
            print("Worker finishing...")

        async def do_work(self, data):
            await asyncio.sleep(2)
            self.result_ready.emit(data * 2)

    worker = BackgroundWorker()
    worker.start(config={'threads': 4})
    worker.queue_task(worker.do_work(10))
    worker.stop()

    See Also
    --------
    t_slot : Decorates methods as thread-safe or async slots.
    t_signal : Decorates functions to define signals.
    """

    class WorkerClass(cls):
        """
        Worker class for the worker pattern.
        """

        def __init__(self):
            self._tsignal_loop = None
            self._tsignal_thread = None

            """
            _tsignal_lifecycle_lock:
                A re-entrant lock that protects worker's lifecycle state (event loop and thread).
                All operations that access or modify worker's lifecycle state must be
                performed while holding this lock.
            """
            self._tsignal_lifecycle_lock = threading.RLock()
            self._tsignal_stopping = asyncio.Event()
            self._tsignal_affinity = object()
            self._tsignal_process_queue_task = None
            self._tsignal_task_queue = None
            super().__init__()

        @property
        def event_loop(self) -> asyncio.AbstractEventLoop:
            """Returns the worker's event loop"""

            if not self._tsignal_loop:
                raise RuntimeError("Worker not started")

            return self._tsignal_loop

        @t_signal
        def started(self):
            """Signal emitted when the worker starts"""

        @t_signal
        def stopped(self):
            """Signal emitted when the worker stops"""

        async def run(self, *args, **kwargs):
            """Run the worker."""

            logger.debug("[WorkerClass][run] calling super")

            super_run = getattr(super(), _WorkerConstants.RUN, None)
            is_super_run_called = False

            if super_run is not None and inspect.iscoroutinefunction(super_run):
                sig = inspect.signature(super_run)

                try:
                    logger.debug("[WorkerClass][run] sig: %s", sig)
                    sig.bind(self, *args, **kwargs)
                    await super_run(*args, **kwargs)
                    logger.debug("[WorkerClass][run] super_run called")
                    is_super_run_called = True
                except TypeError:
                    logger.warning(
                        "[WorkerClass][run] Parent run() signature mismatch. "
                        "Expected: async def run(*args, **kwargs) but got %s",
                        sig,
                    )

            if not is_super_run_called:
                logger.debug("[WorkerClass][run] super_run not called, starting queue")
                await self.start_queue()

        async def _process_queue(self):
            """Process the task queue."""

            while not self._tsignal_stopping.is_set():
                coro = await self._tsignal_task_queue.get()

                try:
                    await coro
                except Exception as e:
                    logger.error(
                        "[WorkerClass][_process_queue] Task failed: %s",
                        e,
                        exc_info=True,
                    )
                finally:
                    self._tsignal_task_queue.task_done()

        async def start_queue(self):
            """Start the task queue processing. Returns the queue task."""

            self._tsignal_process_queue_task = asyncio.create_task(
                self._process_queue()
            )

        def queue_task(self, coro):
            """Method to add a task to the queue"""

            if not asyncio.iscoroutine(coro):
                logger.error(
                    "[WorkerClass][queue_task] Task must be a coroutine object: %s",
                    coro,
                )
                return

            with self._tsignal_lifecycle_lock:
                loop = self._tsignal_loop

            loop.call_soon_threadsafe(lambda: self._tsignal_task_queue.put_nowait(coro))

        def start(self, *args, **kwargs):
            """Start the worker thread."""

            run_coro = kwargs.pop(_WorkerConstants.RUN_CORO, None)

            if run_coro is not None and not asyncio.iscoroutine(run_coro):
                logger.error(
                    "[WorkerClass][start][run_coro] must be a coroutine object: %s",
                    run_coro,
                )
                return

            def thread_main():
                """Thread main function."""

                self._tsignal_task_queue = asyncio.Queue()

                with self._tsignal_lifecycle_lock:
                    self._tsignal_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._tsignal_loop)

                async def runner():
                    """Runner function."""

                    self.started.emit()

                    if run_coro is not None:
                        run_task = asyncio.create_task(run_coro(*args, **kwargs))
                    else:
                        run_task = asyncio.create_task(self.run(*args, **kwargs))

                    try:
                        await self._tsignal_stopping.wait()

                        run_task.cancel()

                        try:
                            await run_task
                        except asyncio.CancelledError:
                            pass

                        if (
                            self._tsignal_process_queue_task
                            and not self._tsignal_process_queue_task.done()
                        ):
                            self._tsignal_process_queue_task.cancel()

                            try:
                                await self._tsignal_process_queue_task
                            except asyncio.CancelledError:
                                logger.debug(
                                    "[WorkerClass][start][thread_main] _process_queue_task cancelled"
                                )

                    finally:
                        self.stopped.emit()
                        # Give the event loop a chance to emit the signal
                        await asyncio.sleep(0)
                        logger.debug("[WorkerClass][start][thread_main] emit stopped")

                with self._tsignal_lifecycle_lock:
                    loop = self._tsignal_loop

                loop.create_task(runner())
                loop.run_forever()
                loop.close()

                with self._tsignal_lifecycle_lock:
                    self._tsignal_loop = None

            # Protect thread creation and assignment under the same lock
            with self._tsignal_lifecycle_lock:
                self._tsignal_thread = threading.Thread(target=thread_main, daemon=True)

            with self._tsignal_lifecycle_lock:
                self._tsignal_thread.start()

        def stop(self):
            """Stop the worker thread."""

            logger.debug("[WorkerClass][stop][START]")

            # Acquire lock to safely access _tsignal_loop and _tsignal_thread
            with self._tsignal_lifecycle_lock:
                loop = self._tsignal_loop
                thread = self._tsignal_thread

            if loop and thread and thread.is_alive():
                logger.debug("[WorkerClass][stop][SET STOPPING]")
                loop.call_soon_threadsafe(self._tsignal_stopping.set)
                logger.debug("[WorkerClass][stop][WAITING FOR THREAD TO JOIN]")
                thread.join(timeout=2)
                logger.debug("[WorkerClass][stop][THREAD JOINED]")

                with self._tsignal_lifecycle_lock:
                    self._tsignal_loop = None
                    self._tsignal_thread = None

        def move_to_thread(self, target):
            """
            Move target object to this worker's thread and loop.
            target must be an object created by t_with_signals or t_with_worker,
            and the worker must be started with start() method.
            """
            with self._tsignal_lifecycle_lock:
                if not self._tsignal_thread or not self._tsignal_loop:
                    raise RuntimeError(
                        "[WorkerClass][move_to_thread] Worker thread not started. "
                        "Cannot move target to this thread."
                    )

            # Assume target is initialized with t_with_signals
            # Reset target's _tsignal_thread, _tsignal_loop, _tsignal_affinity
            if not hasattr(target, "_tsignal_thread") or not hasattr(
                target, "_tsignal_loop"
            ):
                raise TypeError(
                    "[WorkerClass][move_to_thread] Target is not compatible. "
                    "Ensure it is decorated with t_with_signals or t_with_worker."
                )

            # Copy worker's _tsignal_affinity, _tsignal_thread, _tsignal_loop to target
            target._tsignal_thread = self._tsignal_thread
            target._tsignal_loop = self._tsignal_loop
            target._tsignal_affinity = self._tsignal_affinity

            logger.debug(
                "[WorkerClass][move_to_thread] Moved %s to worker thread=%s with affinity=%s",
                target,
                self._tsignal_thread,
                self._tsignal_affinity,
            )

        async def wait_for_stop(self):
            """Wait for the worker to stop."""

            await self._tsignal_stopping.wait()

    return WorkerClass
