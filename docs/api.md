# API Reference

## Decorators

### `@t_with_signals`
Class decorator that enables signal-slot functionality.

**Usage:**
```python
@t_with_signals
class MyClass:
    pass
```

### `@t_signal`
Defines a signal in a class decorated with `@t_with_signals`.

**Usage:**
```python
@t_signal
def signal_name(self):
    pass
```

### `@t_slot`
Marks a method as a slot that can receive signals.

**Usage:**
```python
@t_slot
def on_signal(self, *args, **kwargs):
    pass

@t_slot
async def on_async_signal(self, *args, **kwargs):
    pass
```

## Classes

### `TSignal`
Base class for signals.

#### Methods

##### `connect(receiver: object, slot: Callable, connection_type: Optional[TConnectionType] = None) -> None`
Connects the signal to a slot.

**Parameters:**
- `receiver`: Object that contains the slot
- `slot`: Callable that will receive the signal
- `connection_type`: Optional connection type (DirectConnection or QueuedConnection)

##### `disconnect(receiver: Optional[object] = None, slot: Optional[Callable] = None) -> int`
Disconnects one or more slots from the signal.

**Parameters:**
- `receiver`: Optional receiver to disconnect
- `slot`: Optional slot to disconnect

**Returns:**
- Number of disconnected connections

**Important Behavior Note:**
The disconnection affects only future signal emissions. If a signal has already been emitted and slots are queued for execution, disconnecting will not prevent those queued slots from executing. To ensure a slot doesn't receive a signal, disconnect it before the signal is emitted.

Example of correct disconnection timing:
```python
# This slot will not receive the signal
signal.disconnect(receiver, slot)
signal.emit()

# vs

# This slot might still receive the signal because it was queued before disconnection
signal.emit()
signal.disconnect(receiver, slot)  # Too late to prevent execution
```

This behavior is intentional and ensures:
1. Signal processing remains predictable and thread-safe
2. In-progress operations are not abruptly terminated
3. System state remains consistent during signal processing

For asynchronous slots, the same principle applies:
```python
# Correct:
signal.disconnect(receiver, async_slot)
signal.emit()  # async_slot will not be called

# Might still execute:
signal.emit()  # async_slot is queued
signal.disconnect(receiver, async_slot)  # Won't prevent queued execution
await asyncio.sleep(0.1)  # async_slot might still run
```
##### `emit(*args, **kwargs) -> None`
Emits the signal with the given arguments.

**Parameters:**
- `*args`: Positional arguments to pass to slots
- `**kwargs`: Keyword arguments to pass to slots

### `TConnectionType`
Enum defining connection types.

#### Values:
- `DirectConnection`: Slot is called directly in the emitting thread
- `QueuedConnection`: Slot is queued in the receiver's event loop

## Constants

### `TSignalConstants`
Constants used by the TSignal system.

#### Values:
- `FROM_EMIT`: Key for emission context
- `THREAD`: Key for thread storage
- `LOOP`: Key for event loop storage

## Usage Examples

### Basic Signal-Slot
```python
@t_with_signals
class Sender:
    @t_signal
    def value_changed(self):
        pass

@t_with_signals
class Receiver:
    @t_slot
    def on_value_changed(self, value):
        print(f"Value: {value}")

sender = Sender()
receiver = Receiver()
sender.value_changed.connect(receiver, receiver.on_value_changed)
sender.value_changed.emit(42)
```

### Async Signal-Slot
```python
@t_with_signals
class AsyncReceiver:
    @t_slot
    async def on_value_changed(self, value):
        await asyncio.sleep(1)
        print(f"Value: {value}")

async def main():
    sender = Sender()
    receiver = AsyncReceiver()
    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.value_changed.emit(42)
    await asyncio.sleep(1.1)

asyncio.run(main())
```

### Connection Types
```python
# Force direct connection
sender.value_changed.connect(
    receiver,
    receiver.on_value_changed,
    connection_type=TConnectionType.DirectConnection
)

# Force queued connection
sender.value_changed.connect(
    receiver,
    receiver.on_value_changed,
    connection_type=TConnectionType.QueuedConnection
)
```

## Error Handling

The library raises the following exceptions:

- `AttributeError`: When connecting to None receiver or nonexistent slot
- `TypeError`: When slot is not callable
- `RuntimeError`: When event loop is not available for async operations

Example error handling:
```python
try:
    signal.connect(receiver, slot)
except AttributeError as e:
    logging.error(f"Connection error: {e}")
except TypeError as e:
    logging.error(f"Invalid slot: {e}")
```
