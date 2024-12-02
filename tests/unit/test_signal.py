import pytest
import asyncio
from tsignal.core import TSignal
from tsignal.core import t_with_signals, t_signal, t_slot
from ..conftest import Receiver


def test_signal_creation(sender):
    """Test signal creation and initialization"""
    assert hasattr(sender, "value_changed")
    assert isinstance(sender.value_changed, TSignal)


def test_signal_connection(sender, receiver):
    """Test signal connection"""
    sender.value_changed.connect(receiver, receiver.on_value_changed)
    assert len(sender.value_changed.connections) == 1


def test_invalid_connection(sender, receiver):
    """Test invalid signal connections"""
    with pytest.raises(AttributeError):
        sender.value_changed.connect(None, receiver.on_value_changed)

    with pytest.raises(TypeError):
        sender.value_changed.connect(receiver, "not a callable")

    with pytest.raises(TypeError):
        non_existent_slot = getattr(receiver, "non_existent_slot", None)
        sender.value_changed.connect(receiver, non_existent_slot)


def test_signal_disconnect_all(sender, receiver):
    """Test disconnecting all slots"""
    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.value_changed.connect(receiver, receiver.on_value_changed_sync)

    assert len(sender.value_changed.connections) == 2

    # Disconnect all slots
    disconnected = sender.value_changed.disconnect()
    assert disconnected == 2
    assert len(sender.value_changed.connections) == 0

    # Emit should not trigger any slots
    sender.emit_value(42)
    assert receiver.received_value is None
    assert receiver.received_count == 0


def test_signal_disconnect_specific_slot(sender, receiver):
    """Test disconnecting a specific slot"""
    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.value_changed.connect(receiver, receiver.on_value_changed_sync)

    assert len(sender.value_changed.connections) == 2

    # Disconnect only the sync slot
    disconnected = sender.value_changed.disconnect(slot=receiver.on_value_changed_sync)
    assert disconnected == 1
    assert len(sender.value_changed.connections) == 1

    # Only async slot should remain
    remaining = sender.value_changed.connections[0]
    assert remaining[1] == receiver.on_value_changed


def test_signal_disconnect_specific_receiver(sender, receiver, event_loop):
    """Test disconnecting a specific receiver"""
    # Create another receiver instance
    receiver2 = Receiver()

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.value_changed.connect(receiver2, receiver2.on_value_changed)

    assert len(sender.value_changed.connections) == 2

    # Disconnect receiver1
    disconnected = sender.value_changed.disconnect(receiver=receiver)
    assert disconnected == 1
    assert len(sender.value_changed.connections) == 1

    # Only receiver2 should get the signal
    async def test():
        sender.emit_value(42)
        await asyncio.sleep(0.1)
        assert receiver.received_value is None
        assert receiver2.received_value == 42

    event_loop.run_until_complete(test())


def test_signal_disconnect_specific_receiver_and_slot(sender, receiver):
    """Test disconnecting a specific receiver-slot combination"""
    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.value_changed.connect(receiver, receiver.on_value_changed_sync)

    assert len(sender.value_changed.connections) == 2

    # Disconnect specific receiver-slot combination
    disconnected = sender.value_changed.disconnect(
        receiver=receiver, slot=receiver.on_value_changed
    )
    assert disconnected == 1
    assert len(sender.value_changed.connections) == 1

    # Only sync slot should remain
    remaining = sender.value_changed.connections[0]
    assert remaining[1] == receiver.on_value_changed_sync


def test_signal_disconnect_nonexistent(sender, receiver):
    """Test disconnecting slots that don't exist"""
    sender.value_changed.connect(receiver, receiver.on_value_changed)

    # Try to disconnect nonexistent slot
    disconnected = sender.value_changed.disconnect(
        receiver=receiver, slot=receiver.on_value_changed_sync
    )
    assert disconnected == 0
    assert len(sender.value_changed.connections) == 1

    # Try to disconnect nonexistent receiver
    other_receiver = Receiver()  # Create another instance
    disconnected = sender.value_changed.disconnect(receiver=other_receiver)
    assert disconnected == 0
    assert len(sender.value_changed.connections) == 1


@pytest.mark.asyncio
async def test_signal_disconnect_during_emit(sender, receiver, event_loop):
    """Test disconnecting slots while emission is in progress"""

    @t_with_signals
    class SlowReceiver:
        def __init__(self):
            super().__init__()
            self.received_value = None

        @t_slot
        async def on_value_changed(self, value):
            await asyncio.sleep(0.1)
            self.received_value = value

    slow_receiver = SlowReceiver()
    sender.value_changed.connect(slow_receiver, slow_receiver.on_value_changed)
    sender.value_changed.connect(receiver, receiver.on_value_changed)

    # Disconnect first, then emit
    sender.value_changed.disconnect(receiver=receiver)
    sender.emit_value(42)  # Changed emission order

    await asyncio.sleep(0.2)

    assert slow_receiver.received_value == 42
    assert receiver.received_value is None


def test_direct_function_connection(sender):
    """Test direct connection of lambda and regular functions"""
    received_values = []

    def collect_value(value):
        received_values.append(value)

    # Connect lambda function
    sender.value_changed.connect(lambda v: received_values.append(v * 2))

    # Connect regular function
    sender.value_changed.connect(collect_value)

    # Emit signal
    sender.emit_value(42)

    assert 42 in received_values  # Added by collect_value
    assert 84 in received_values  # Added by lambda function (42 * 2)
    assert len(received_values) == 2


@pytest.mark.asyncio
async def test_direct_async_function_connection(sender):
    """Test direct connection of async functions"""
    received_values = []

    async def async_collector(value):
        await asyncio.sleep(0.1)
        received_values.append(value)

    # Connect async function
    sender.value_changed.connect(async_collector)

    # Emit signal
    sender.emit_value(42)

    # Wait for async processing
    await asyncio.sleep(0.2)

    assert received_values == [42]


def test_direct_function_disconnect(sender):
    """Test disconnection of directly connected functions"""
    received_values = []

    collector = lambda v: received_values.append(v)
    sender.value_changed.connect(collector)

    # First emit
    sender.emit_value(42)
    assert received_values == [42]

    # Disconnect
    disconnected = sender.value_changed.disconnect(slot=collector)
    assert disconnected == 1

    # Second emit - should not add value since connection is disconnected
    sender.emit_value(43)
    assert received_values == [42]


def test_method_connection_with_signal_attributes(sender):
    """Test connecting a method with _thread and _loop attributes automatically sets up receiver"""
    received_values = []

    @t_with_signals
    class SignalReceiver:
        def collect_value(self, value):
            received_values.append(value)

    class RegularClass:
        def collect_value(self, value):
            received_values.append(value * 2)

    # t_with_signals가 적용된 객체의 메소드
    signal_receiver = SignalReceiver()
    sender.value_changed.connect(signal_receiver.collect_value)

    # 일반 객체의 메소드
    regular_receiver = RegularClass()
    sender.value_changed.connect(regular_receiver.collect_value)

    # Emit signal
    sender.emit_value(42)

    # signal_receiver는 QueuedConnection으로 처리되어야 함
    connection = next(
        conn
        for conn in sender.value_changed.connections
        if conn[1] == signal_receiver.collect_value
    )
    assert connection[0] == signal_receiver  # receiver가 자동으로 설정됨

    # regular_receiver는 DirectConnection으로 처리되어야 함
    connection = next(
        conn
        for conn in sender.value_changed.connections
        if hasattr(conn[1], "__wrapped__")
    )
    assert connection[0] is None  # receiver가 None임

    assert 42 in received_values  # SignalReceiver의 결과
    assert 84 in received_values  # RegularClass의 결과 (42 * 2)
