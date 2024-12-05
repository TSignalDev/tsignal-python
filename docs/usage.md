# Usage Guide

## Requirements
TSignal requires Python 3.10 or higher.

## Table of Contents
1. [Basic Concepts](#basic-concepts)
2. [Signals](#signals)
3. [Slots](#slots)
4. [Connection Types](#connection-types)
5. [Threading and Async](#threading-and-async)
6. [Best Practices](#best-practices)
7. [Worker Thread Pattern](#worker-thread-pattern)

## Basic Concepts
TSignal implements the signal-slot pattern, which allows for loose coupling between components. The core concepts are:

- **Signal**: An event that can be emitted when something happens
- **Slot**: A function that receives and handles the signal
- **Connection**: The link between a signal and a slot

## Signals

### Defining Signals
Signals are defined using the `@t_signal` decorator:
```python
@t_with_signals
class Button:
    @t_signal
    def clicked(self):
        """Signal emitted when button is clicked"""
        pass

    def click(self):
        self.clicked.emit()
```

### Emitting Signals
Signals can emit any number of arguments:
```python
@t_with_signals
class Sensor:
    @t_signal
    def reading_changed(self):
        """Signal emitted when sensor reading changes"""
        pass

    def update_reading(self, value, timestamp):
        self.reading_changed.emit(value, timestamp)
```

## Slots

### Defining Slots
Slots are defined using the `@t_slot` decorator:
```python
@t_with_signals
class Display:
    @t_slot
    def on_reading_changed(self, value, timestamp):
        print(f"New reading at {timestamp}: {value}")
```

### Async Slots
Slots can be asynchronous:
```python
@t_with_signals
class DataProcessor:
    @t_slot
    async def on_data_received(self, data):
        result = await self.process_data(data)
        print(f"Processed result: {result}")
```

## Connection Types
TSignal supports two types of connections:

### DIRECT_CONNECTION
- Signal and slot execute in the same thread
- Slot is called immediately when signal is emitted
```python
signal.connect(receiver, slot, connection_type=TConnectionType.DIRECT_CONNECTION)
```

### QUEUED_CONNECTION
- Signal and slot can execute in different threads
- Slot execution is queued in receiver's event loop
```python
signal.connect(receiver, slot, connection_type=TConnectionType.QUEUED_CONNECTION)
```

Connection type is automatically determined based on:
- Whether the slot is async
- Whether signal and slot are in different threads

## Threading and Async

### Thread Safety
TSignal handles thread-safe signal emission automatically:
```python
@t_with_signals
class Worker:
    @t_signal
    def progress_changed(self):
        pass

    def work(self):
        for i in range(100):
            # Can safely emit from any thread
            self.progress_changed.emit(i)
```

### Async Context
When using async slots, ensure you're in an async context:
```python
async def main():
    worker = Worker()
    processor = AsyncProcessor()
    
    worker.progress_changed.connect(processor, processor.on_progress)
    worker_thread = threading.Thread(target=worker.work)
    worker_thread.start()
    
    # Keep event loop running
    while worker_thread.is_alive():
        await asyncio.sleep(0.1)
```

## Best Practices

1. **Signal Naming**
   - Use verb-noun format for signals
   - Use past tense for events that have occurred
   ```python
   value_changed
   data_received
   connection_lost
   ```

2. **Slot Naming**
   - Prefix with 'on_' to indicate event handler
   - Match signal name when possible
   ```python
   on_value_changed
   on_data_received
   on_connection_lost
   ```

3. **Resource Cleanup**
   - Disconnect signals when they're no longer needed
   ```python
   # Disconnect specific slot
   signal.disconnect(receiver, slot)
   
   # Disconnect all slots
   signal.disconnect()
   ```

4. **Error Handling**
   - Always handle exceptions in slots
   - Signal emission continues even if one slot fails
   ```python
   @t_slot
   def on_data_received(self, data):
       try:
           self.process_data(data)
       except Exception as e:
           logging.error(f"Error processing data: {e}")
   ```

## Resource Management

### Signal Disconnection
Disconnecting signals requires careful consideration of timing. The disconnection only affects future signal emissions and cannot cancel already queued slot executions.

#### Disconnection Timing
```python
@t_with_signals
class DataSource:
    @t_signal
    def data_updated(self):
        pass

@t_with_signals
class DataProcessor:
    @t_slot
    async def on_data_updated(self, data):
        await self.process_data(data)

# Correct disconnection timing
source = DataSource()
processor = DataProcessor()

# This ensures processor won't receive the signal
source.data_updated.disconnect(processor, processor.on_data_updated)
source.data_updated.emit(some_data)

# vs

# CAUTION: This might still execute the slot
source.data_updated.emit(some_data)  # Slot is queued for execution
source.data_updated.disconnect(processor, processor.on_data_updated)  # Too late
```

#### Why This Matters
This behavior is particularly important in scenarios such as:

1. Resource Cleanup
```python
class ViewManager:
    def cleanup_view(self, view):
        # Disconnect before any potential final updates
        data_source.value_changed.disconnect(view, view.update)
        # Now any cleanup operations...
        view.cleanup()
```

2. Thread Safety
```python
@t_with_signals
class WorkerThread:
    def stop(self):
        # Disconnect signal handlers before stopping
        self.progress_updated.disconnect()
        # Then stop the thread...
        self.thread.join()
```

3. Async Operations
```python
async def switch_data_processor(old_processor, new_processor):
    # Disconnect old processor first
    data_source.data_ready.disconnect(old_processor, old_processor.process)
    # Wait for any pending processing to complete
    await old_processor.wait_pending()
    # Connect new processor
    data_source.data_ready.connect(new_processor, new_processor.process)
```

#### Best Practices

1. Early Disconnection
   - Disconnect signals before any operations that might emit them
   - Don't rely on disconnection to stop already queued slot executions

2. Clean Shutdown
```python
class Application:
    def shutdown(self):
        # 1. Disconnect all signals
        self.event_bus.disconnect_all()
        # 2. Stop worker threads
        self.stop_workers()
        # 3. Cleanup resources
        self.cleanup()
```

3. Resource Lifecycle
```python
class ManagedResource:
    def __init__(self, signal_source):
        self.signal_source = signal_source
        self.connections = []
        
    def connect_handlers(self):
        # Store connections for proper cleanup
        self.connections.append(
            (self.signal_source.updated, self.on_update)
        )
        self.signal_source.updated.connect(self, self.on_update)
    
    def cleanup(self):
        # Disconnect all signals before cleanup
        for signal, slot in self.connections:
            signal.disconnect(self, slot)
        self.connections.clear()
```

This understanding of signal disconnection behavior is crucial for:
- Preventing memory leaks
- Ensuring proper resource cleanup
- Managing complex async operations
- Handling thread synchronization correctly

## Signal Connection Types

### Object-Member Connection
Traditional signal-slot connection between objects:
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

sender.value_changed.connect(receiver, receiver.on_value_changed)
```

### Function Connection
Connect signals directly to functions or lambdas:
```python
# Standalone function
def handle_value(value):
    print(f"Value: {value}")
sender.value_changed.connect(handle_value)

# Lambda function
sender.value_changed.connect(lambda x: print(f"Value: {x}"))
```

### Method Connection
Connect to object methods without @t_slot decorator:
```python
class Handler:
    def process(self, value):
        print(f"Processing: {value}")

handler = Handler()
sender.value_changed.connect(handler.process)
```

### Connection Behavior Notes
- Object-member connections are automatically disconnected when the receiver is destroyed
- Function connections remain active until explicitly disconnected
- Method connections behave like function connections and need manual cleanup

## Worker Thread Pattern

### Overview
The worker pattern provides a convenient way to run operations in a background thread with built-in signal/slot support and task queuing.

### Basic Worker
```python
@t_with_worker
class ImageProcessor:
    async def initialize(self, cache_size=100):
        """Called when worker starts"""
        self.cache = {}
        self.cache_size = cache_size
    
    async def finalize(self):
        """Called before worker stops"""
        self.cache.clear()
    
    @t_signal
    def processing_complete(self):
        """Signal emitted when processing is done"""
        pass
    
    async def process_image(self, image_data):
        """Task to be executed in worker thread"""
        result = await self.heavy_processing(image_data)
        self.processing_complete.emit(result)

# Usage
processor = ImageProcessor()
processor.start(cache_size=200)

# Queue tasks
await processor.queue_task(processor.process_image(data1))
await processor.queue_task(processor.process_image(data2))

# Cleanup
processor.stop()
```

### Worker Features

#### Thread Safety
- All signal emissions are thread-safe
- Task queue is thread-safe
- Worker has its own event loop

#### Task Queue
- Tasks are executed sequentially
- Tasks must be coroutines
- Queue is processed in worker thread

#### Lifecycle Management
```python
@t_with_worker
class Worker:
    async def initialize(self, *args, **kwargs):
        # Setup code
        self.resources = await setup_resources()
    
    async def finalize(self):
        # Cleanup code
        await self.resources.cleanup()
    
    async def some_task(self):
        # Will run in worker thread
        await self.resources.process()

worker = Worker()
try:
    worker.start()
    await worker.queue_task(worker.some_task())
finally:
    worker.stop()  # Ensures cleanup
```

#### Combining with Signals
Workers can use signals to communicate results:
```python
@t_with_worker
class DataProcessor:
    def __init__(self):
        super().__init__()
        self.results = []
    
    @t_signal
    def processing_done(self):
        """Emitted when batch is
