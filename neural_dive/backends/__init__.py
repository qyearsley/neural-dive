"""Rendering backends for Neural Dive.

This package provides different rendering backends that implement the RenderBackend protocol:
- BlessedBackend: Real terminal rendering using blessed library
- TestBackend: Mock backend for unit testing
"""

from neural_dive.backends.backend import RenderBackend
from neural_dive.backends.blessed_backend import BlessedBackend
from neural_dive.backends.test_backend import DrawCall, TestBackend

__all__ = [
    "RenderBackend",
    "BlessedBackend",
    "TestBackend",
    "DrawCall",
]
