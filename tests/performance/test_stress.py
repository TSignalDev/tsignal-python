"""
Test cases for stress testing.
"""

import asyncio
import pytest
from tsignal import t_with_signals, t_signal, t_slot

# pylint: disable=no-member
# pylint: disable=redefined-outer-name
# pylint: disable=unused-variable

@pytest.mark.asyncio
async def test_heavy_signal_load():
    """Test heavy signal load"""
    @t_with_signals
    class Sender:
        """Sender class"""
        @t_signal
        def signal(self):
            """Signal method"""

    @t_with_signals
    class Receiver:
        """Receiver class"""
        @t_slot
        async def slot(self):
            """Slot method"""
            await asyncio.sleep(0.001)

    sender = Sender()
    receivers = [Receiver() for _ in range(100)]
    for r in receivers:
        sender.signal.connect(r, r.slot)

    for _ in range(1000):
        sender.signal.emit()
