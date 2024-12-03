from memory_profiler import profile
import pytest
from tsignal import t_with_signals, t_signal, t_slot

@pytest.mark.performance
@profile
def test_memory_usage():
    # 시그널/슬롯 생성 및 제거 반복
    for _ in range(1000):
        sender = create_complex_signal_chain()
        sender.signal.disconnect()

def create_complex_signal_chain():
    @t_with_signals
    class Sender:
        @t_signal
        def signal(self): pass

    @t_with_signals
    class Receiver:
        @t_slot
        def slot(self, value):
            pass

    sender = Sender()
    receivers = [Receiver() for _ in range(100)]
    for r in receivers:
        sender.signal.connect(r, r.slot)
    return sender 