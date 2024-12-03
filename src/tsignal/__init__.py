"""
TSignal - Python Signal/Slot Implementation
"""

from .core import (
    t_with_signals,
    t_signal,
    t_slot,
    TConnectionType,
)
from .contrib.patterns.worker.decorators import t_with_worker

__version__ = "0.1.0"

__all__ = [
    "t_with_signals",
    "t_signal",
    "t_slot",
    "t_with_worker",
    "TConnectionType",
]
