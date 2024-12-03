import asyncio
import pytest
from tsignal import t_with_signals, t_signal, t_slot

@pytest.mark.asyncio
async def test_heavy_signal_load():
    @t_with_signals
    class Sender:
        @t_signal
        def signal(self): pass

    @t_with_signals
    class Receiver:
        @t_slot
        async def slot(self, value):
            await asyncio.sleep(0.001)

    sender = Sender()
    receivers = [Receiver() for _ in range(100)]
    for r in receivers:
        sender.signal.connect(r, r.slot)

    for _ in range(1000):
        sender.signal.emit()
