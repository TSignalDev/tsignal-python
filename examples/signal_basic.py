# examples/signal_basic.py

"""
Basic Signal-Slot Example

This example demonstrates the fundamental usage of TSignal with a synchronous slot:
1. Creating a signal
2. Connecting a regular method as a slot (without @t_slot)
3. Emitting a signal to trigger slot execution

Key Points:
- Showcases the most basic form of signal-slot connection.
- The slot is a normal instance method of a class, not decorated with @t_slot.
- Emphasizes that even without @t_slot, a callable method can act as a slot.
- Introduces the concept of signal emission and immediate slot execution.
"""

import asyncio
import time
from tsignal.core import t_with_signals, t_signal, t_slot


@t_with_signals
class Counter:
    """
    A simple counter class that emits a signal when its count changes.
    """

    def __init__(self):
        self.count = 0

    @t_signal
    def count_changed(self):
        """Signal emitted when count changes"""

    def increment(self):
        """Increment counter and emit signal"""
        self.count += 1
        print(f"Counter incremented to: {self.count}")
        self.count_changed.emit(self.count)


@t_with_signals
class Display:
    """
    A simple display class that receives count updates and processes them.
    """

    def __init__(self):
        self.last_value = None

    def on_count_changed(self, value):
        """slot that receives count updates"""
        print(f"Display processing count: {value}")
        # Simulate some heavy processing
        time.sleep(1)
        self.last_value = value
        print(f"Display finished processing: {value}")


async def main():
    """
    Main function to run the async counter example.
    """

    # Create instances
    counter = Counter()
    display = Display()

    # Connect signal to slot
    counter.count_changed.connect(display.on_count_changed)

    print("Starting counter example...")
    print("Press Enter to increment counter, or 'q' to quit")
    print("(Notice the 1 second delay in processing)")

    while True:
        line = input("> ")

        if line.lower() == "q":
            break

        # Increment counter which will emit signal
        counter.increment()


if __name__ == "__main__":
    asyncio.run(main())
