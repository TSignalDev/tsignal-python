"""
Test cases for threading.
"""

import asyncio
import threading
from time import sleep


def test_different_thread_connection(sender, receiver, event_loop):
    """Test signal emission from different thread"""
    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender_done = threading.Event()

    def run_sender():
        """Run the sender thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for i in range(3):
            sender.emit_value(i)
            sleep(0.1)
        sender_done.set()
        loop.close()

    async def wait_for_receiver():
        """Wait for the receiver to receive the signals"""
        while not sender_done.is_set() or receiver.received_count < 3:
            await asyncio.sleep(0.1)

    sender_thread = threading.Thread(target=run_sender)
    sender_thread.start()
    event_loop.run_until_complete(wait_for_receiver())
    sender_thread.join()

    assert receiver.received_count == 3
    assert receiver.received_value == 2


def test_call_slot_from_other_thread(receiver, event_loop):
    """Test calling slot from different thread"""
    done = threading.Event()

    def other_thread():
        """Run the other thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def call_slot():
            await receiver.on_value_changed(100)

        loop.run_until_complete(call_slot())
        done.set()
        loop.close()

    thread = threading.Thread(target=other_thread)
    thread.start()

    while not done.is_set():
        event_loop.run_until_complete(asyncio.sleep(0.1))

    thread.join()
    assert receiver.received_value == 100
    assert receiver.received_count == 1
