"""
Test cases for the slot pattern.
"""

import asyncio
import pytest
from tsignal import t_with_signals, t_slot


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
