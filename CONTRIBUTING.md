# Contributing to TSignal

Thank you for your interest in contributing to TSignal! This document provides guidelines and instructions for contributing to the project.

## Development Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/TSignalDev/tsignal-python.git
cd tsignal-python
```

2. Create a virtual environment and install development dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

## Code Style

We follow these coding conventions:
- PEP 8 style guide
- Maximum line length of 88 characters (Black default)
- Type hints for function arguments and return values
- Docstrings for all public modules, functions, classes, and methods

## Testing

Run the test suite before submitting changes:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tsignal

# Run specific test file
pytest tests/unit/test_signal.py

# Enable debug logging during tests
TSIGNAL_DEBUG=1 pytest
```

## Pull Request Process

1. Create a new branch for your feature or bugfix:
```bash
git checkout -b feature-name
```

2. Make your changes and commit them:
```bash
git add .
git commit -m "Description of changes"
```

3. Ensure your changes include:
   - Tests for any new functionality
   - Documentation updates if needed
   - No unnecessary debug prints or commented code
   - Type hints for new functions/methods

4. Push your changes and create a pull request:
```bash
git push origin feature-name
```

5. In your pull request description:
   - Describe what the changes do
   - Reference any related issues
   - Note any breaking changes
   - Include examples if applicable

## Development Guidelines

### Adding New Features

1. Start with tests
2. Implement the feature
3. Update documentation
4. Add examples if applicable

### Debug Logging

Use appropriate log levels:
```python
import logging

logger = logging.getLogger(__name__)

# Debug information
logger.debug("Detailed connection info")

# Important state changes
logger.info("Signal connected successfully")

# Warning conditions
logger.warning("Multiple connections detected")

# Errors
logger.error("Failed to emit signal", exc_info=True)
```

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Focus on constructive criticism
- Accept feedback gracefully
- Put the project's best interests first

### Enforcement

Violations of the code of conduct may result in:
1. Warning
2. Temporary ban
3. Permanent ban

Report issues to project maintainers via email.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).
