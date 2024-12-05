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

### `@t_with_worker`
Class decorator that creates a worker thread with signal support and task queue.

**Requirements:**
- Class must implement async `initialize(self, *args, **kwargs)` method
- Class must implement async `finalize(self)` method

**Added Methods:**
##### `start(*args, **kwargs) -> None`
Starts the worker thread and calls initialize with given arguments.

##### `stop() -> None`
Stops the worker thread gracefully, calling finalize.

##### `async queue_task(coro) -> None`
Queues a coroutine for execution in the worker thread.

**Example:**
```python
@t_with_worker
class Worker:
    async def initialize(self):
        print("Worker initialized")
    
    async def finalize(self):
        print("Worker cleanup")
    
    async def process(self):
        await asyncio.sleep(1)
        print("Processing done")

worker = Worker()
worker.start()
await worker.queue_task(worker.process())
worker.stop()
```

## Classes

### `TSignal`
Base class for signals.

#### Methods

##### `connect(receiver_or_slot: Union[object, Callable], slot: Optional[Callable] = None) -> None`
Connects the signal to a slot.

**Parameters:**
- When connecting to a QObject slot:
  - `receiver_or_slot`: The receiver object
  - `slot`: The slot method of the receiver

- When connecting to a function/lambda:
  - `receiver_or_slot`: The callable (function, lambda, or method)
  - `slot`: None

**Connection Behavior:**
1. Object Method with Signal Support:
   ```python
   @t_with_signals
   class Receiver:
       def on_signal(self, value):
           print(value)
   
   receiver = Receiver()
   signal.connect(receiver.on_signal)  # Automatically sets up receiver
   ```

2. Regular Object Method:
   ```python
   class RegularClass:
       def on_signal(self, value):
           print(value)
   
   obj = RegularClass()
   signal.connect(obj.on_signal)  # Treated as direct connection
   ```

The connection type is automatically determined:
- Methods from objects with `@t_with_signals` are set up with their object as receiver
- Regular object methods are treated as direct connections
- Async methods always use queued connections

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
- `DIRECT_CONNECTION`: Slot is called directly in the emitting thread
- `QUEUED_CONNECTION`: Slot is queued in the receiver's event loop

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
    connection_type=TConnectionType.DIRECT_CONNECTION
)

# Force queued connection
sender.value_changed.connect(
    receiver,
    receiver.on_value_changed,
    connection_type=TConnectionType.QUEUED_CONNECTION
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
