"""
Test cases for the with-signal pattern.
"""

import asyncio
from tests.conftest import Receiver


def test_same_thread_connection(sender, receiver, event_loop):
    """Test signal-slot connection in same thread"""

    async def test():
        sender.value_changed.connect(receiver, receiver.on_value_changed)
        sender.emit_value(42)
        await asyncio.sleep(0.1)
        assert receiver.received_value == 42
        assert receiver.received_count == 1

    event_loop.run_until_complete(test())


def test_multiple_slots(sender, event_loop):
    """Test multiple slot connections"""
    receiver1 = Receiver()
    receiver2 = Receiver()

    sender.value_changed.connect(receiver1, receiver1.on_value_changed)
    sender.value_changed.connect(receiver2, receiver2.on_value_changed)

    async def test():
        """Test the multiple slot connections"""
        sender.emit_value(42)
        await asyncio.sleep(0.1)
        assert receiver1.received_value == 42
        assert receiver1.received_count == 1
        assert receiver2.received_value == 42
        assert receiver2.received_count == 1

    event_loop.run_until_complete(test())
