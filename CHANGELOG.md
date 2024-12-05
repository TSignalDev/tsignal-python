# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-03-19

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
