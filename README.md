# TSignal

A Python Signal-Slot library inspired by Qt

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
        """Signal emitted when count changes"""
        pass
    
    def increment(self):
        self.count += 1
        self.count_changed.emit(self.count)

@t_with_signals
class Display:
    @t_slot
    def on_count_changed(self, value):
        print(f"Count is now: {value}")

# Usage
counter = Counter()
display = Display()

# Connect signal to slot
counter.count_changed.connect(display, display.on_count_changed)

# Increment will trigger signal emission
counter.increment()  # Output: Count is now: 1
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
