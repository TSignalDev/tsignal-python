# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2024-12-28

### Important Notice
- **Package Deprecation**: TSignal is being rebranded to Pynnex. This version marks the beginning of the deprecation period.
- All future development will continue at [github.com/nexconnectio/pynnex](https://github.com/nexconnectio/pynnex)
- Users are encouraged to migrate to the new package: `pip install pynnex`

### Changed
- Updated all repository URLs to point to the new Pynnex repository
- Added deprecation warnings when importing the package
- Updated package metadata to reflect deprecated status

## [0.4.0] - 2024-12-21

### Added
- **Weak Reference Support**: Introduced `weak=True` for signal connections to allow automatic disconnection when the receiver is garbage-collected.
- **One-Shot Connections**: Added `one_shot=True` in `connect(...)` to enable automatically disconnecting a slot after its first successful emission call.
- Extended integration tests to cover new `weak` and `one_shot` functionality.

### Improved
- **Thread Safety**: Strengthened internal locking and concurrency patterns to reduce race conditions in high-load or multi-threaded environments.
- **Documentation**: Updated `readme.md`, `api.md`, and example code sections to explain weak references, one-shot usage, and improved thread-safety details.

## [0.3.0] - 2024-12-19

### Changed
- Removed `initialize` and `finalize` methods from the worker thread.

### Added
- Added the following examples:
  - `signal_function_slots.py` for demonstrating signal/slot connection with a regular function
  - `signal_lambda_slots.py` for demonstrating signal/slot connection with a lambda function
  - `stock_core.py` for demonstrating how to configure and communicate with a threaded backend using signal/slot and event queue
  - `stock_monitor_console.py` for demonstrating how to configure and communicate with a threaded backend in a command line interface
  - `stock_monitor_ui.py` for demonstrating how to configure and communicate with a threaded backend in a GUI.

### Fixed
- Fixed issues with regular function and lambda function connections.
- Fixed issues with the worker thread's event queue and graceful shutdown.

### Note
Next steps before 1.0.0:
- Strengthening Stability
  - Resource Cleanup Mechanism/Weak Reference Support:
    - Consider supporting weak references (weakref) that automatically release signal/slot connections when the object is GC'd.
  - Handling Slot Return Values in Async/Await Flow:
    - A mechanism may be needed to handle the values or exceptions returned by async slots.
      Example: If a slot call fails, the emit side can detect and return a callback or future.
  - Strengthening Type Hint-Based Verification:
    - The functionality of comparing the slot signature and the type of the passed argument when emitting can be further extended.
      - Read the type hint for the slot function, and if the number or type of the arguments does not match when emitting, raise a warning or exception.
- Consider Additional Features
  - One-shot or Limited Connection Functionality:
      A "one-shot" slot feature that listens to a specific event only once and then disconnects can be provided.
        Example: Add the connect_one_shot method.
        Once the event is received, it will automatically disconnect.

## [0.2.0] - 2024-12-6

### Changed
- Updated minimum Python version requirement to 3.10
  - This change was necessary to ensure reliable worker thread functionality
  - Python 3.10+ provides improved async features and type handling
  - Better support for async context management and error handling
- Updated documentation to reflect new Python version requirement
- Enhanced worker thread implementation with Python 3.10+ features

### Added
- Performance tests for stress testing and memory usage analysis
  - Includes `test_stress.py` for heavy signal load testing
  - Includes `test_memory.py` for memory profiling

### Removed
- Support for Python versions below 3.10

### Note
Core features are now implemented and stable:
- Robust signal-slot mechanism
- Thread-safe operations
- Async/await support
- Worker thread pattern
- Comprehensive documentation
- Full test coverage

Next steps before 1.0.0:
- Additional stress testing
- Memory leak verification
- Production environment validation
- Enhanced CI/CD pipeline
- Extended documentation

## [0.1.1] - 2024-12-01

### Changed
- Refactored signal connection logic to support direct function connections
- Improved error handling for invalid connections
- Enhanced logging for signal emissions and connections

### Fixed
- Resolved issues with disconnecting slots during signal emissions
- Fixed bugs related to async slot processing and connection management

### Removed
- Deprecated unused constants and methods from the core module

## [0.1.0] - 2024-01-26

### Added
- Initial release
- Basic signal-slot mechanism with decorators
- Support for both synchronous and asynchronous slots
- Thread-safe signal emissions
- Automatic connection type detection
- Comprehensive test suite
- Full documentation
