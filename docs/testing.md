# Testing Guide

## Overview
TSignal uses pytest for testing. Our test suite includes unit tests, integration tests, and supports async testing.

## Test Structure
```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures and configurations
├── unit/               # Unit tests
│   ├── __init__.py
│   ├── test_signal.py
│   ├── test_slot.py
│   └── test_with_signals.py
└── integration/        # Integration tests
    ├── __init__.py
    ├── test_async.py
    └── test_threading.py
```

## Running Tests

### Basic Test Commands
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with very verbose output
pytest -vv

# Run with print statements visible
pytest -s

# Run specific test file
pytest tests/unit/test_signal.py

# Run specific test case
pytest tests/unit/test_signal.py -k "test_signal_disconnect_all"

# Run tests by marker
pytest -v -m asyncio
```

### Debug Mode
To enable debug logging during tests:
```bash
# Windows
set TSIGNAL_DEBUG=1
pytest tests/unit/test_signal.py -v

# Linux/Mac
TSIGNAL_DEBUG=1 pytest tests/unit/test_signal.py -v
```

### Test Coverage
To run tests with coverage report:
```bash
# Run tests with coverage
pytest --cov=tsignal

# Generate HTML coverage report
pytest --cov=tsignal --cov-report=html
```
