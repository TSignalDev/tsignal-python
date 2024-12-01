# TSignal

Are you looking for a signal/slot pattern in Python without Qt dependencies? TSignal provides a lightweight, thread-safe, and asyncio-compatible implementation that gives you all the power of Qt's signal/slot pattern without the heavyweight dependencies. Perfect for:

- Async applications needing event handling
- Thread communication in Python applications
- Event-driven architectures
- Decoupled component communication

## Why TSignal?
- 🚀 Pure Python implementation - no Qt or external dependencies required
- ⚡ Async/await support out of the box
- 🔒 Thread-safe signal emission and slot execution
- 🎯 Simple, decorator-based API similar to Qt
- 🔄 Automatic thread handling for cross-thread signals

## Quick Start

### Basic Example
```python
from tsignal import t_with_signals, t_signal, t_slot

@t_with_signals
class Counter:
    def __init__(self):
        self.count = 0
    
    @t_signal
    def count_changed(self):
        pass
    
    def increment(self):
        self.count += 1
        self.count_changed.emit(self.count)

@t_with_signals
class Display:
    @t_slot
    async def on_count_changed(self, value):
        print(f"Count is now: {value}")

# Connect and use
counter = Counter()
display = Display()
counter.count_changed.connect(display, display.on_count_changed)
counter.increment()  # Will print: "Count is now: 1"
```

### Async Example
```python
@t_with_signals
class AsyncDisplay:
    @t_slot
    async def on_count_changed(self, value):
        await asyncio.sleep(1)  # Simulate async operation
        print(f"Count updated to: {value}")

# Usage in async context
async def main():
    counter = Counter()
    display = AsyncDisplay()
    
    counter.count_changed.connect(display, display.on_count_changed)
    counter.increment()
    
    # Wait for async processing
    await asyncio.sleep(1.1)

asyncio.run(main())
```

## Features
- Easy-to-use signal-slot mechanism with decorators
- Support for both synchronous and asynchronous slots
- Thread-safe signal emissions
- Automatic connection type detection (direct/queued)
- Compatible with Python's asyncio

## Installation

Currently, this package is under development. You can install it directly from the repository:

```bash
git clone https://github.com/tsignal/tsignal-python.git
cd tsignal-python
pip install -e .
```

For development installation (includes test dependencies):
```bash
pip install -e ".[dev]"
```

## Documentation
- [Detailed Usage Guide](docs/usage.md)
- [API Reference](docs/api.md)
- [Examples](docs/examples.md)
- [Logging Guidelines](docs/logging.md)
- [Testing Guide](docs/testing.md)

## Development

### Logging
TSignal uses Python's standard logging module. For detailed logging configuration, 
please see [Logging Guidelines](docs/logging.md).

Basic usage:
```python
import logging
logging.getLogger('tsignal').setLevel(logging.INFO)
```

## Testing

TSignal includes a comprehensive test suite using pytest. For basic testing:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_signal.py
```

For detailed testing instructions and guidelines, see [Testing Guide](docs/testing.md).

## Contributing
Please see [Contributing Guidelines](CONTRIBUTING.md) for details on how to contribute to this project.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Connecting Signals and Slots

### Classic Object-Member Connection
```python
@t_with_signals
class Counter:
    @t_signal
    def count_changed(self):
        pass

@t_with_signals
class Display:
    @t_slot
    def on_count_changed(self, value):
        print(f"Count is now: {value}")

counter = Counter()
display = Display()
counter.count_changed.connect(display, display.on_count_changed)
```

### Function Connection
```python
# Connect to a simple function
def print_value(value):
    print(f"Value: {value}")
    
counter.count_changed.connect(print_value)

# Connect to a lambda
counter.count_changed.connect(lambda x: print(f"Lambda received: {x}"))

# Connect to an object method without @t_slot
class Handler:
    def process_value(self, value):
        print(f"Processing: {value}")
        
handler = Handler()
counter.count_changed.connect(handler.process_value)
```

## Worker Thread Pattern

TSignal provides a worker thread pattern that combines thread management with signal/slot communication and task queuing:

```python
from tsignal import t_with_worker

@t_with_worker
class DataProcessor:
    async def initialize(self, config=None):
        # Setup worker (called in worker thread)
        self.config = config or {}
    
    async def process_data(self, data):
        # Heavy processing in worker thread
        result = await heavy_computation(data)
        self.processing_done.emit(result)
    
    async def finalize(self):
        # Cleanup worker (called before thread stops)
        await self.cleanup()

    @t_signal
    def processing_done(self):
        pass

# Usage
processor = DataProcessor()
processor.start(config={'threads': 4})  # Starts worker thread

# Queue task in worker thread
await processor.queue_task(processor.process_data(some_data))

# Stop worker
processor.stop()  # Graceful shutdown
```

The worker pattern provides:
- Dedicated worker thread with event loop
- Built-in signal/slot support
- Async task queue
- Graceful initialization/shutdown
- Thread-safe communication
