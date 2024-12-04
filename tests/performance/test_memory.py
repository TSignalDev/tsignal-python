"""
Test cases for memory usage.
"""

# pylint: disable=no-member
# pylint: disable=redefined-outer-name
# pylint: disable=unused-variable

from memory_profiler import profile
import pytest
from tsignal import t_with_signals, t_signal, t_slot

@pytest.mark.performance
@profile
def test_memory_usage():
    """Test memory usage"""
    # Create and delete signal/slot pairs repeatedly
    for _ in range(1000):
        sender = create_complex_signal_chain()
        sender.signal.disconnect()

def create_complex_signal_chain():
    """Create a complex signal chain"""
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
        def slot(self, value):
            """Slot method"""

    sender = Sender()
    receivers = [Receiver() for _ in range(100)]
    for r in receivers:
        sender.signal.connect(r, r.slot)
    return sender
