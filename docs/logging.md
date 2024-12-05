# Logging Guidelines

## Requirements
TSignal requires Python 3.10 or higher.

TSignal uses Python's standard logging module with the following levels:

- DEBUG: Detailed information about signal-slot connections and emissions
- INFO: Important state changes and major events
- WARNING: Potential issues that don't affect functionality
- ERROR: Exceptions and failures

To enable debug logging in tests:
```bash
TSIGNAL_DEBUG=1 pytest
```

Configure logging in your application:
```python
import logging
logging.getLogger('tsignal').setLevel(logging.INFO)
```
